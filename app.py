from pathlib import Path
import streamlit as st


from config.prompts.services.prompt_manager import PromptManager

from config.prompts.services.prompt_registry import PromptRegistry


from llm.groq_service import LLMService

from llm.services.summarizer import Summarizer

from pipeline.chunking.chunker import TranscriptChunker

from storage.services.transcript_service import TranscriptService

from video_processor.services.parser import extract_video_id


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


if "classification" not in st.session_state:
    st.session_state.classification = None


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

        st.success("Loaded summary from database.")

    else:

        with st.spinner("Processing video..."):

            # -------------------------
            # Chunk transcript
            # -------------------------

            chunker = TranscriptChunker(3)

            chunks = chunker.chunk(
                transcript.segments,
                transcript.video_id,
            )

            # -------------------------
            # Vector Store
            # -------------------------

            embedding_service = services["embedding"]

            vectors = embedding_service.embed_chunks(chunks)

            store = services["store"]

            store.delete_collection()

            store.upsert(chunks, vectors)

            # -------------------------
            # Summarization
            # -------------------------

            summarizer = services["summarizer"]

            summary = summarizer.summarize(chunks)

            classification = summarizer.classify_summary(summary)

            transcript.summary = summary

            transcript.classification = classification

            transcript_service.save(transcript)

    # -------------------------
    # Session storage
    # -------------------------

    st.session_state.summary = summary

    st.session_state.classification = classification

    st.session_state.retriever = services["retriever"]

    st.session_state.generator = services["generator"]


# --------------------------------------------------
# Display Summary
# --------------------------------------------------

if st.session_state.summary:

    st.subheader("📝 Summary")

    st.json(st.session_state.summary)

    st.subheader("🏷️ Classification")

    st.json(st.session_state.classification)

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
