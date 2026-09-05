"""from pathlib import Path
import streamlit as st

from config.prompts.services.prompt_manager import PromptManager  # type: ignore
from config.prompts.services.prompt_registry import PromptRegistry  # type: ignore

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

    prompt_manager = PromptManager(base_path=(Path(__file__).parent / "config/prompts"))

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
                st.markdown(
                    f"**{term.get('term', '')}** — {term.get('definition', '')}"
                )
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
                        st.code(
                            block.get("content", ""), language=block.get("language", "")
                        )
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
            st.markdown(
                f"**{concept.get('name', '')}** — {concept.get('definition', '')}"
            )

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
                st.markdown(
                    f"- **{issue.get('claim', '')}** — {issue.get('reason', '')}"
                )

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


# print(transcript.text)"""

import asyncio
import logging
from typing import Any

import streamlit as st

from l2_layer import layer2_content_parse
from l3_layer import layer3_knowledge_graph
from l5_layer import layer5_deep_dive
from l6_layer import layer6_synthesis
from l7_layer import layer7_study_assets

from llm.groq_service import LLMService
from llm.gemini_service import GeminiService

from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id
from pipeline.chunking.chunker import TranscriptChunker

# RAG components from the older, working pipeline.
from pipeline.embeddings.embedder import EmbeddingService
from pipeline.rag.context_builder import ContextBuilder
from pipeline.rag.generator import Generator
from pipeline.retrieval.retriever import Retriever
from pipeline.vectorstore.qdrant_store import QdrantStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="MindBook",
    page_icon="📚",
    layout="wide",
)

st.title("📚 MindBook")
st.caption("YouTube → L2 → L3 → L5 → L6 → L7 → RAG")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def format_timestamp(seconds: Any) -> str:
    try:
        total = int(float(seconds or 0))
    except (TypeError, ValueError):
        total = 0

    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def run_pipeline(url_or_id: str) -> dict:
    """Run the current MindBook L2-L7 pipeline once."""

    video_id = extract_video_id(url_or_id)

    transcript_service = TranscriptService()
    transcript = transcript_service.get(video_id)

    video_info = transcript.video_info or {}

    # Current working model split:
    # L2 -> Groq
    # L3 -> Gemini
    # L5 -> Groq
    # L6 -> Gemini
    # L7 -> Groq
    groq_llm = LLMService()
    gemini_llm = GeminiService()

    # ---------------------------------------------------------------
    # L2
    # ---------------------------------------------------------------

    l2_result = asyncio.run(
        layer2_content_parse(
            transcript=transcript,
            video_info=video_info,
            llm_service=gemini_llm,
        )
    )

    

    # ---------------------------------------------------------------
    # L3
    # ---------------------------------------------------------------

    l3_result = asyncio.run(
        layer3_knowledge_graph(
            layer2_result=l2_result,
            transcript=transcript.segments,
            video_info=video_info,
            llm_service=groq_llm,
        )
    )

    # ---------------------------------------------------------------
    # Chunking
    # ---------------------------------------------------------------

    chunker = TranscriptChunker(
        version=TranscriptChunker.VERSION_SEMANTIC,
        max_words=300,
        overlap_words=50,
    )

    chunks = chunker.chunk(
        segments=transcript.segments,
        video_id=video_id,
        chapters=video_info.get("chapters"),
        duration=video_info.get("duration"),
    )

    # ---------------------------------------------------------------
    # L5
    # ---------------------------------------------------------------

    sections = []

    for index, chunk in enumerate(chunks):
        st.write(f"Analyzing section {index + 1}/{len(chunks)}...")

        l5_result = asyncio.run(
            layer5_deep_dive(
                chunk=chunk,
                video_info=video_info,
                parsed=l2_result,
                llm_service=groq_llm,
            )
        )

        section = dict(l5_result)

        # Preserve chunk metadata, as in the current CLI pipeline.
        section["chunk_id"] = chunk.get("chunk_id")
        section["title"] = chunk.get("title") or "Untitled Section"
        section["start"] = chunk.get("start", 0)
        section["end"] = chunk.get("end", section["start"])
        section["word_count"] = chunk.get("word_count", 0)

        sections.append(section)

    # ---------------------------------------------------------------
    # L6
    # ---------------------------------------------------------------

    l6_result = asyncio.run(
        layer6_synthesis(
            video_info=video_info,
            sections=sections,
            parsed=l2_result,
            kg=l3_result,
            llm_service=gemini_llm,
        )
    )

    # ---------------------------------------------------------------
    # L7
    # ---------------------------------------------------------------

    l7_result = asyncio.run(
        layer7_study_assets(
            sections=sections,
            synthesis=l6_result,
            kg=l3_result,
            parsed=l2_result,
            llm_service=groq_llm,
        )
    )

    # ---------------------------------------------------------------
    # RAG
    # ---------------------------------------------------------------

    rag_error = None

    try:
        embedding_service = EmbeddingService()
        store = QdrantStore()

        vectors = embedding_service.embed_chunks(chunks)

        # Keep the old MVP behavior: replace the collection for a
        # freshly generated video.
        store.delete_collection()
        store.upsert(chunks, vectors)

        retriever = Retriever(embedding_service, store)
        context_builder = ContextBuilder()
        generator = Generator()

    except Exception as exc:
        logger.exception("RAG setup failed")
        retriever = None
        context_builder = None
        generator = None
        rag_error = str(exc)

    return {
        "video_id": video_id,
        "video_info": video_info,
        "transcript": transcript,
        "chunks": chunks,
        "l2": l2_result,
        "l3": l3_result,
        "sections": sections,
        "l6": l6_result,
        "l7": l7_result,
        "retriever": retriever,
        "context_builder": context_builder,
        "generator": generator,
        "rag_error": rag_error,
    }


# ---------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------

url_or_id = st.text_input(
    "YouTube URL or Video ID",
    placeholder="https://youtu.be/... or Qb9s3UiMSTA",
)

if st.button("🚀 Generate MindBook", type="primary"):
    if not url_or_id.strip():
        st.warning("Please enter a YouTube URL or video ID.")
    else:
        try:
            with st.status("Building your MindBook...", expanded=True) as status:
                st.write("Running L2: Content Parse...")
                result = run_pipeline(url_or_id.strip())
                status.update(
                    label="MindBook generated successfully!",
                    state="complete",
                    expanded=False,
                )

            st.session_state["mindbook"] = result

        except Exception as exc:
            logger.exception("MindBook pipeline failed")
            st.error(f"Pipeline failed: {exc}")
            st.exception(exc)


# ---------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------

result = st.session_state.get("mindbook")

if result:
    video_info = result["video_info"]
    l2 = result["l2"]
    l3 = result["l3"]
    sections = result["sections"]
    l6 = result["l6"]
    l7 = result["l7"]

    st.divider()

    # ================================================================
    # Video
    # ================================================================

    st.header(video_info.get("title") or "MindBook")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Video ID", result["video_id"])

    with col2:
        st.metric(
            "Duration",
            format_timestamp(video_info.get("duration", 0)),
        )

    with col3:
        st.metric("Sections", len(sections))

    # ================================================================
    # L2 — Content Parse
    # ================================================================

    with st.expander("🧠 L2 — Content Analysis", expanded=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**Content Type**")
            st.write(l2.get("content_type", "—"))

        with c2:
            st.markdown("**Domain**")
            st.write(l2.get("domain", "—"))

        with c3:
            st.markdown("**Difficulty**")
            st.write(l2.get("difficulty", "—"))

        if l2.get("overall_topic"):
            st.markdown("### Overall Topic")
            st.write(l2["overall_topic"])

        if l2.get("learning_objectives"):
            st.markdown("### Learning Objectives")
            for item in l2["learning_objectives"]:
                st.markdown(f"- {item}")

        if l2.get("prerequisites"):
            st.markdown("### Prerequisites")
            for item in l2["prerequisites"]:
                st.markdown(f"- {item}")

    # ================================================================
    # L3 — Knowledge Graph
    # ================================================================

    with st.expander("🕸️ L3 — Knowledge Graph", expanded=False):
        nodes = l3.get("nodes", [])
        edges = l3.get("edges", [])

        st.write(f"**Nodes:** {len(nodes)}  |  **Edges:** {len(edges)}")

        if nodes:
            st.markdown("### Concepts")
            for node in nodes:
                st.markdown(
                    f"- **{node.get('label', '')}** " f"({node.get('type', 'concept')})"
                )

        if l3.get("dependency_order"):
            st.markdown("### Dependency Order")
            st.write(" → ".join(l3["dependency_order"]))

        if l3.get("mermaid"):
            st.markdown("### Mermaid")
            st.code(l3["mermaid"], language="mermaid")

    # ================================================================
    # L5 — Deep Dive
    # ================================================================

    st.header("📖 Deep Dive")

    if not sections:
        st.info("No L5 sections were generated.")
    else:
        for index, section in enumerate(sections, start=1):
            title = section.get("title") or f"Section {index}"
            start = format_timestamp(section.get("start", 0))
            end = format_timestamp(section.get("end", 0))

            difficulty = section.get("difficulty_rating")

            label = f"{index}. {title} · {start}–{end}"

            if difficulty is not None:
                label += f" · Difficulty {difficulty}/5"

            with st.expander(label, expanded=(index == 1)):
                for block in section.get("blocks", []):
                    block_type = block.get("type")
                    content = block.get("content", "")

                    if block_type == "heading":
                        st.markdown(f"### {content}")

                    elif block_type == "paragraph":
                        st.markdown(content)

                    elif block_type == "code":
                        st.code(
                            content,
                            language=block.get("language", ""),
                        )

                    elif block_type == "table":
                        st.markdown(content)

                    elif block_type == "callout":
                        variant = block.get("variant", "note")

                        if variant == "warning":
                            st.warning(content)
                        else:
                            st.info(content)

                    elif content:
                        st.markdown(content)

                concepts = section.get("key_concepts", [])
                if concepts:
                    st.caption("Key concepts: " + " · ".join(map(str, concepts)))

                sketch = section.get("sketch_note") or {}

                if sketch:
                    st.markdown("#### ✏️ Sketch Note")

                    if sketch.get("title"):
                        st.markdown(f"**{sketch['title']}**")

                    if sketch.get("subtitle"):
                        st.write(sketch["subtitle"])

                    for box in sketch.get("boxes", []):
                        st.markdown(f"- {box}")

                    if sketch.get("takeaway"):
                        st.success(sketch["takeaway"])

    # ================================================================
    # L6 — Synthesis
    # ================================================================

    with st.expander("📚 L6 — Complete Summary", expanded=True):
        if l6.get("executive_summary"):
            st.markdown("### Executive Summary")
            st.markdown(l6["executive_summary"])

        if l6.get("complete_guide"):
            st.markdown("### Complete Guide")
            st.markdown(l6["complete_guide"])

        if l6.get("key_terms"):
            st.markdown("### 🔤 Key Terms")
            for term in l6["key_terms"]:
                if isinstance(term, dict):
                    st.markdown(
                        f"**{term.get('term', '')}** — " f"{term.get('definition', '')}"
                    )
                else:
                    st.markdown(f"- {term}")

        if l6.get("faq"):
            st.markdown("### ❓ FAQ")
            for item in l6["faq"]:
                if isinstance(item, dict):
                    st.markdown(f"**Q: {item.get('q', '')}**")
                    st.write(item.get("a", ""))
                else:
                    st.write(item)

        if l6.get("key_insights"):
            st.markdown("### 💡 Key Insights")
            for item in l6["key_insights"]:
                st.markdown(f"- {item}")

        if l6.get("related_concepts"):
            st.markdown("### 🔗 Related Concepts")
            for item in l6["related_concepts"]:
                st.markdown(f"- {item}")

        if l6.get("next_steps"):
            st.markdown("### 🪜 Next Steps")
            for item in l6["next_steps"]:
                st.markdown(f"- {item}")

        if l6.get("flashcards"):
            st.markdown("### 🗂️ Flashcards")
            for card in l6["flashcards"]:
                if isinstance(card, dict):
                    st.markdown(f"**{card.get('front', '')}**")
                    st.write(card.get("back", ""))
                    st.divider()

    # ================================================================
    # L7 — Study Assets
    # ================================================================

    with st.expander("🎯 L7 — Study Assets", expanded=True):
        quiz = l7.get("quiz", [])

        if quiz:
            st.markdown("### 📝 Quiz")

            for index, question in enumerate(quiz, start=1):
                st.markdown(f"**{index}. {question.get('question', '')}**")

                options = question.get("options", [])
                for option in options:
                    st.markdown(f"- {option}")

                if question.get("explanation"):
                    with st.expander("Show answer"):
                        st.write(f"**Correct:** " f"{question.get('correct', '')}")
                        st.write(question["explanation"])
        else:
            st.info("No quiz questions were generated.")

        timeline = l7.get("concept_timeline", [])

        if timeline:
            st.markdown("### ⏱️ Concept Timeline")

            for item in timeline:
                st.markdown(
                    f"**{format_timestamp(item.get('timestamp', 0))}** — "
                    f"{item.get('concept', '')} "
                    f"({item.get('importance', 'medium')})"
                )

        mind_map = l7.get("mind_map_text", "")

        if mind_map:
            st.markdown("### 🗺️ Mind Map")
            st.code(mind_map)

    # ================================================================
    # RAG — Ask Questions
    # ================================================================

    st.divider()
    st.header("💬 Ask MindBook")

    if result.get("rag_error"):
        st.warning(
            "The L2-L7 pipeline completed, but RAG could not be initialized: "
            + result["rag_error"]
        )
    elif result.get("retriever") is None:
        st.warning("RAG is not available for this run.")
    else:
        question = st.text_input(
            "Ask anything about this video",
            key="mindbook_question",
            placeholder="What is the main idea explained here?",
        )

        if st.button("Ask", type="secondary"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                try:
                    with st.spinner("Searching the video..."):
                        retrieved = result["retriever"].retrieve(
                            question.strip(),
                            limit=5,
                        )

                        context = result["context_builder"].build(retrieved)

                        answer = result["generator"].generate(
                            question.strip(),
                            context,
                        )

                    st.markdown("### Answer")
                    st.write(answer)

                except Exception as exc:
                    logger.exception("RAG question failed")
                    st.error(f"Could not answer the question: {exc}")
else:
    st.info("Enter a YouTube URL above and click **Generate MindBook**.")
