from pathlib import Path
import streamlit as st

from config.prompts.services.prompt_manager import PromptManager
from llm.groq_service import LLMService
from llm.services.summarizer import Summarizer
from processing.services.chunker import TranscriptChunker
from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id


st.set_page_config(page_title="YouTube Summarizer", layout="wide")

st.title("🎥 YouTube Video Summarizer")

url = st.text_input("Enter YouTube URL")

if st.button("Generate Summary"):

    if not url:
        st.warning("Please enter a YouTube URL.")
        st.stop()

    with st.spinner("Loading transcript..."):

        video_id = extract_video_id(url)

        t_service = TranscriptService()
        transcript = t_service.get(video_id)

    if transcript.summary:

        summary = transcript.summary
        classification = transcript.classification

        st.success("Loaded summary from database.")

    else:

        with st.spinner("Summarizing video..."):

            chunker = TranscriptChunker(max_words=325)
            chunks = chunker.chunk(transcript.text)

            llm = LLMService()

            prompt = PromptManager(
                Path(__file__).parent / "config" / "prompts"
            )

            summarizer = Summarizer(
                llm=llm,
                prompts=prompt,
            )

            summary = summarizer.summarize(chunks)
            classification = summarizer.classify_summary(summary)

            transcript.summary = summary
            transcript.classification = classification

            # Uncomment if you want to save
            # t_service.save(transcript)

    st.subheader("📝 Summary")
    st.write(summary)

    st.subheader("🏷 Classification")
    st.success(classification)

    with st.expander("Transcript"):
        st.write(transcript.text)







#print(transcript.text)


