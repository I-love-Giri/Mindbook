from pathlib import Path

from config.prompts.services.prompt_manager import PromptManager
from llm.groq_service import LLMService
from llm.services.summarizer import Summarizer
from processing.services.chunker import TranscriptChunker
from storage.services.transcript_service import TranscriptService
from video_processor.services.parser import extract_video_id


url = input("Enter a YouTube URL: ")

video_id = extract_video_id(url)

t_service = TranscriptService()
transcript = t_service.get(video_id)

if transcript.summary:
    print("Summary loaded from DB")
    summary = transcript.summary
else:
    chunker = TranscriptChunker(max_words=325)
    chunks = chunker.chunk(transcript.text)

    llm = LLMService()

    #summary_prompt = Path("prompts/summary.txt").read_text(encoding="utf-8")
    #combine_prompt = Path("prompts/combine_summary.txt").read_text(encoding="utf-8")

    #prompt = PromptManager("prompts")

    prompt = prompt_manager = PromptManager(Path(__file__).parent / "config" / "prompts")

    summarizer = Summarizer(
        llm=llm,
        prompts= prompt
        #summary_prompt=summary_prompt,
        #combine_prompt=combine_prompt,
    )

    summary = summarizer.summarize(chunks)
    classification = summarizer.classify_summary(summary)

    transcript.summary = summary
    transcript.classification = classification  # if your model has this field

    #t_service.save(transcript)

print(summary)

if transcript.classification:
    print("Classfication :")
else:

    llm = LLMService()


    prompt = prompt_manager = PromptManager(Path(__file__).parent / "config" / "prompts")


    summarizer = Summarizer(
        llm=llm,
        prompts= prompt
        #summary_prompt=summary_prompt,
        #combine_prompt=combine_prompt,
    )

    classification = summarizer.classify_summary(transcript.summary)
    transcript.classification = classification

print(classification)






#print(transcript.text)


