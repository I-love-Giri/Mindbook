from pathlib import Path
import streamlit as st

from config.prompts.services.prompt_manager import PromptManager
from config.prompts.services.prompt_registry import PromptRegistry

from llm.groq_service import LLMService
from llm.services.summarizer import Summarizer

from pipeline.chunking.chunker import TranscriptChunker

from storage.services.transcript_service import TranscriptService

from video_processor.services.parser import extract_video_id
from video_processor.services.video_info import extract_chapters_and_info

from pipeline.embeddings.embedder import EmbeddingService
from pipeline.rag.context_builder import ContextBuilder
from pipeline.rag.generator import Generator
from pipeline.retrieval.retriever import Retriever
from pipeline.vectorstore.qdrant_store import QdrantStore

# --------------------------------------------------
# Streamlit Config
# --------------------------------------------------

st.set_page_config(page_title="YouTube Summarizer", layout="wide")

st.title("🎥 YouTube Video Summarizer")


# --------------------------------------------------
# Dependency Container
# --------------------------------------------------

@st.cache_resource
def get_services():

    prompt_manager = PromptManager(
        base_path=(Path(__file__).parent / "config/prompts")
    )

    prompt_registry = PromptRegistry(prompt_manager)

    llm = LLMService()

    summarizer = Summarizer(
        llm=llm,
        prompts=prompt_registry,
    )

    embedding_service = EmbeddingService()

    store = QdrantStore()

    retriever = Retriever(embedding_service, store)

    generator = Generator()

    return {
        "summarizer": summarizer,
        "embedding": embedding_service,
        "store": store,
        "retriever": retriever,
        "generator": generator,
    }


services = get_services()


# --------------------------------------------------
# Session State
# --------------------------------------------------

if "summary" not in st.session_state:
    st.session_state.summary = None

if "sections" not in st.session_state:
    st.session_state.sections = None

if "classification" not in st.session_state:
    st.session_state.classification = None

if "key_concepts" not in st.session_state:
    st.session_state.key_concepts = None

if "grounding" not in st.session_state:
    st.session_state.grounding = None

if "retriever" not in st.session_state:
    st.session_state.retriever = None

if "generator" not in st.session_state:
    st.session_state.generator = None


# --------------------------------------------------
# Input
# --------------------------------------------------

url = st.text_input("Enter YouTube URL")


# --------------------------------------------------
# Generate Summary
# --------------------------------------------------

if st.button("Generate Summary"):

    if not url:
        st.warning("Please enter a YouTube URL.")
        st.stop()

    with st.spinner("Loading transcript..."):

        video_id = extract_video_id(url)

        transcript_service = TranscriptService()

        transcript = transcript_service.get(video_id)

    if transcript.summary:

        summary = transcript.summary
        classification = transcript.classification
        sections = getattr(transcript, "sections", None)
        key_concepts = getattr(transcript, "key_concepts", None)
        grounding = getattr(transcript, "grounding", None)

        st.success("Loaded summary from database.")

    else:

        with st.spinner("Processing video..."):

            # -------------------------
            # Chunk transcript
            # -------------------------
            # Chapter-aware chunking needs real chapter markers, which
            # YoutubeTranscriptService does NOT provide - it only
            # fetches transcript text/timing via youtube_transcript_api.
            # Chapters and duration come from a separate source
            # (yt-dlp), fetched here. If this fails or the video has no
            # chapters, extract_chapters_and_info() returns an empty
            # result and chunk() gracefully falls back to its original
            # whole-transcript behavior - this never blocks summary
            # generation, it's a quality enhancement when available.

            with st.spinner("Fetching chapter info..."):
                video_meta = extract_chapters_and_info(transcript.video_id)

            chapters = video_meta.get("chapters") or None
            duration = video_meta.get("duration") or None

            chunker = TranscriptChunker(3)

            chunks = chunker.chunk(
                transcript.segments,
                transcript.video_id,
                chapters=chapters,
                duration=duration,
            )

            # -------------------------
            # Vector Store
            # -------------------------

            embedding_service = services["embedding"]

            vectors = embedding_service.embed_chunks(chunks)

            store = services["store"]

            store.delete_collection()

            store.upsert(chunks, vectors)

        with st.spinner("Generating deep summary..."):

            # -------------------------
            # Deep Summarization Pipeline
            # -------------------------
            # Runs: chunk_summary -> domain_classifier ->
            # section_analysis -> key_concepts ->
            # chapter_summary (hierarchical) -> video_summary ->
            # grounding_checker

            summarizer = services["summarizer"]

            result = summarizer.summarize(chunks)

            summary = result["summary"]
            sections = result["sections"]
            classification = result["classification"]
            key_concepts = result["key_concepts"]
            grounding = result["grounding"]

            transcript.summary = summary
            transcript.sections = sections
            transcript.classification = classification
            transcript.key_concepts = key_concepts
            transcript.grounding = grounding

            transcript_service.save(transcript)

    # -------------------------
    # Session storage
    # -------------------------

    st.session_state.summary = summary
    st.session_state.sections = sections
    st.session_state.classification = classification
    st.session_state.key_concepts = key_concepts
    st.session_state.grounding = grounding
    st.session_state.retriever = services["retriever"]
    st.session_state.generator = services["generator"]


# --------------------------------------------------
# Display Summary
# --------------------------------------------------

if st.session_state.summary:

    summary = st.session_state.summary

    st.subheader(f"📝 {summary.get('title', 'Summary')}")

    if summary.get("executive_summary"):
        st.markdown(f"**{summary['executive_summary']}**")

    if summary.get("complete_guide"):
        with st.expander("📖 Complete Guide", expanded=True):
            st.markdown(summary["complete_guide"])

    if summary.get("major_topics"):
        st.markdown("#### Major Topics")
        for topic in summary["major_topics"]:
            st.markdown(f"**{topic.get('topic', '')}** — {topic.get('summary', '')}")

    if summary.get("key_insights"):
        st.markdown("#### Key Insights")
        for insight in summary["key_insights"]:
            st.markdown(f"- {insight}")

    if summary.get("faq"):
        st.markdown("#### FAQ")
        for item in summary["faq"]:
            src = item.get("source_section")
            label = f" *(section {src})*" if src else ""
            st.markdown(f"**Q: {item.get('q', '')}**{label}")
            st.markdown(f"A: {item.get('a', '')}")

    if summary.get("gaps"):
        st.info(f"**What this may have missed:** {summary['gaps']}")

    if summary.get("key_terms"):
        with st.expander("🔤 Key Terms"):
            for term in summary["key_terms"]:
                st.markdown(f"**{term.get('term', '')}** — {term.get('definition', '')}")
                if term.get("example"):
                    st.caption(term["example"])

    if summary.get("flashcards"):
        with st.expander("🗂️ Flashcards"):
            for card in summary["flashcards"]:
                st.markdown(f"**{card.get('front', '')}**")
                st.markdown(card.get("back", ""))
                st.divider()

    if summary.get("related_concepts") or summary.get("next_steps"):
        col1, col2 = st.columns(2)
        with col1:
            if summary.get("related_concepts"):
                st.markdown("#### Related Concepts")
                for c in summary["related_concepts"]:
                    st.markdown(f"- {c}")
        with col2:
            if summary.get("next_steps"):
                st.markdown("#### Next Steps")
                for s in summary["next_steps"]:
                    st.markdown(f"- {s}")

    if summary.get("final_takeaway"):
        st.success(f"**Takeaway:** {summary['final_takeaway']}")

    if st.session_state.sections:
        st.divider()
        st.subheader("📚 Sections")
        def _format_timestamp(seconds: float) -> str:
            total = int(seconds or 0)
            m, s = divmod(total, 60)
            h, m = divmod(m, 60)
            return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

        for i, section in enumerate(st.session_state.sections):
            title = section.get("title", f"Section {i + 1}")
            timestamp = _format_timestamp(section.get("start", 0))
            difficulty = section.get("difficulty_rating")

            label = f"{title} · {timestamp}"
            if difficulty is not None:
                label += f" · Difficulty {difficulty}/5"

            with st.expander(label):
                for block in section.get("blocks", []):
                    btype = block.get("type")
                    if btype == "heading":
                        st.markdown(f"##### {block.get('content', '')}")
                    elif btype == "paragraph":
                        st.markdown(block.get("content", ""))
                    elif btype == "code":
                        st.code(block.get("content", ""), language=block.get("language", ""))
                        if block.get("caption"):
                            st.caption(block["caption"])
                    elif btype == "table":
                        st.markdown(block.get("content", ""))
                    elif btype == "callout":
                        variant = block.get("variant", "note")
                        content = block.get("content", "")
                        if variant == "warning":
                            st.warning(f"⚠️ {content}")
                        else:
                            st.info(f"💡 {content}")

                if section.get("key_concepts"):
                    st.caption("Key concepts: " + " · ".join(section["key_concepts"]))

    st.subheader("🏷️ Classification")

    classification = st.session_state.classification

    if not classification:
        st.caption("No classification available for this summary.")
    else:
        category = classification.get("category", "unknown")
        difficulty = classification.get("difficulty", "unknown")
        confidence = classification.get("confidence")

        badge = f"**{category.title()}** · {difficulty.title()}"
        if confidence is not None:
            badge += f" · {confidence:.0%} confidence"

        st.markdown(badge)

        if classification.get("reason"):
            st.caption(classification["reason"])

    if st.session_state.key_concepts:
        st.subheader("🔑 Key Concepts")
        for concept in st.session_state.key_concepts:
            st.markdown(f"**{concept.get('name', '')}** — {concept.get('definition', '')}")

    if st.session_state.grounding:
        grounding = st.session_state.grounding
        verdict = grounding.get("verdict")

        with st.expander("✅ Grounding Check", expanded=(verdict == "fail")):

            if verdict == "fail":
                st.warning(
                    "Some parts of the summary may not be fully "
                    "supported by the transcript."
                )
            elif verdict == "pass":
                st.success("This summary checks out against the analyzed content.")

            confidence = grounding.get("confidence")
            if confidence is not None:
                st.caption(f"Confidence: {confidence:.0%}")

            for issue in grounding.get("issues", []):
                st.markdown(f"- **{issue.get('claim', '')}** — {issue.get('reason', '')}")

    st.divider()

    st.subheader("💬 Ask Questions About The Video")

    query = st.text_input("Ask a question", key="question_input")

    if st.button("Get Answer"):

        if query.strip():

            with st.spinner("Generating answer..."):

                retriever = st.session_state.retriever

                results = retriever.retrieve(
                    query,
                    limit=5,
                )

                context_builder = ContextBuilder()

                context = context_builder.build(results)

                answer = st.session_state.generator.generate(
                    query,
                    context,
                )

            st.markdown("### Answer")
            st.write(answer)

        else:
            st.warning("Please enter a question.")

    # st.subheader("🏷 Classification")
    # st.success(classification)

    # with st.expander("Transcript"):
    #    st.write(transcript.text)


# print(transcript.text)
