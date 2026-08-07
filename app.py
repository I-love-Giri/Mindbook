from pathlib import Path

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
# Dependency Container
# --------------------------------------------------


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

    retriever = Retriever(
        embedding_service,
        store,
    )

    generator = Generator()

    return {
        "summarizer": summarizer,
        "embedding": embedding_service,
        "store": store,
        "retriever": retriever,
        "generator": generator,
    }


# --------------------------------------------------
# Generate Summary
# --------------------------------------------------


def generate_summary(url, services):

    if not url:
        raise ValueError("YouTube URL is required.")

    # -------------------------
    # Load Transcript
    # -------------------------

    video_id = extract_video_id(url)

    transcript_service = TranscriptService()

    transcript = transcript_service.get(video_id)

    # -------------------------
    # Load Existing Summary
    # -------------------------

    if transcript.summary:

        return {
            "summary": transcript.summary,
            "classification": transcript.classification,
            "retriever": services["retriever"],
            "generator": services["generator"],
        }

    # -------------------------
    # Chunk Transcript
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

    store.upsert(
        chunks,
        vectors,
    )

    # -------------------------
    # Summarization
    # -------------------------

    summarizer = services["summarizer"]

    summary = summarizer.summarize(chunks)

    classification = summarizer.classify_summary(summary)

    # -------------------------
    # Save Result
    # -------------------------

    transcript.summary = summary

    transcript.classification = classification

    transcript_service.save(transcript)

    return {
        "summary": summary,
        "classification": classification,
        "retriever": services["retriever"],
        "generator": services["generator"],
    }


# --------------------------------------------------
# Question Answering
# --------------------------------------------------


def ask_question(query, retriever, generator):

    if not query.strip():
        raise ValueError("Question cannot be empty.")

    results = retriever.retrieve(
        query,
        limit=5,
    )

    context_builder = ContextBuilder()

    context = context_builder.build(results)

    answer = generator.generate(
        query,
        context,
    )

    return answer


# --------------------------------------------------
# CLI Execution Example
# --------------------------------------------------

if __name__ == "__main__":

    services = get_services()

    youtube_url = input("Enter YouTube URL: ")

    result = generate_summary(
        youtube_url,
        services,
    )

    print("\nSummary:")
    print(result["summary"])

    print("\nClassification:")
    print(result["classification"])

    while True:

        question = input("\nAsk a question (or type exit): ")

        if question.lower() == "exit":
            break

        answer = ask_question(
            question,
            result["retriever"],
            result["generator"],
        )

        print("\nAnswer:")
        print(answer)

    # st.subheader("🏷 Classification")
    # st.success(classification)

    # with st.expander("Transcript"):
    #    st.write(transcript.text)


# print(transcript.text)
