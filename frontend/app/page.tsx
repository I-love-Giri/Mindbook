"use client";

import { useState } from "react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<any>(null);
  const [videoId, setVideoId] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");

  const [selectedAnswers, setSelectedAnswers] = useState<{
    [key: number]: string;
  }>({});

  const [checkedAnswers, setCheckedAnswers] = useState<{
    [key: number]: boolean;
  }>({});

  const handleGenerate = async () => {
    if (!url.trim()) {
      setMessage("Please enter a YouTube URL.");
      return;
    }

    setMessage("Sending request...");

    try {
      const response = await fetch("http://127.0.0.1:8000/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url,
        }),
      });

      if (!response.ok) {
        throw new Error("Request failed");
      }

      const data = await response.json();

      setVideoId(data.video_id);

      setMessage("Processing started...");

      checkStatus(data.video_id);
    } catch (error) {
      console.error(error);
      setMessage("Could not connect to FastAPI.");
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) {
      return;
    }

    if (!videoId) {
      setAskError("Please generate a MindBook first.");
      return;
    }

    setAsking(true);
    setAnswer("");
    setAskError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          video_id: videoId,
          question: question,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get answer");
      }

      const data = await response.json();

      setAnswer(data.answer);
    } catch (error) {
      console.error(error);
      setAskError("Could not get an answer.");
    } finally {
      setAsking(false);
    }
  };

  const checkStatus = async (videoId: string) => {
    const statusUrl = `http://127.0.0.1:8000/status/${videoId}`;

    console.log("Checking status:", statusUrl);

    const response = await fetch(statusUrl);

    console.log("Status response:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.log("Status error:", errorText);

      throw new Error("Could not check status");
    }

    const data = await response.json();

    console.log("Status data:", data);

    setMessage(`Status: ${data.status}`);

    if (data.status === "processing") {
      setTimeout(() => {
        checkStatus(videoId);
      }, 2000);
    }

    if (data.status === "completed") {
      setMessage("Your MindBook is ready! 🎉");

      const resultResponse = await fetch(
        `http://127.0.0.1:8000/result/${videoId}`
      );

      if (!resultResponse.ok) {
        throw new Error("Could not fetch MindBook result");
      }

      const result = await resultResponse.json();

      console.log("MindBook Result:", result);

      setResult(result);
    }

    if (data.status === "failed") {
      setMessage("Processing failed ❌");
    }
  };

  return (
    <main className="min-h-screen bg-[#0D0D10] text-[#E8E7EC]">
      <div className="min-h-screen">
        {/* Navbar */}
        <nav className="sticky top-0 z-50 h-16 border-b border-white/[0.08] bg-[#0D0D10]/95 backdrop-blur">
          <div className="mx-auto flex h-full max-w-[1500px] items-center justify-between px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#B08DFF] font-serif text-lg text-[#0D0D10]">
                M
              </div>

              <div>
                <div className="font-serif text-lg tracking-tight text-white">
                  MindBook
                </div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-[#71717A]">
                  Learning workspace
                </div>
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm text-[#8F8D96]">
              <span className="hidden md:block">Study smarter</span>
              <button className="border border-white/[0.1] px-4 py-2 text-[#C8C5CF] transition hover:border-[#B08DFF]/50 hover:text-white">
                My Library
              </button>
            </div>
          </div>
        </nav>
        {/* Hero Section */}
        <section className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-[1100px] flex-col items-center justify-center px-6 text-center">
          <h2 className="max-w-4xl font-serif text-5xl font-normal leading-[1.05] tracking-[-0.025em] text-white md:text-7xl">
            Learn from videos.
            <br />
            <span className="text-[#B08DFF]">Remember what you learn.</span>
          </h2>

          <p className="mt-7 max-w-2xl text-[17px] leading-8 text-[#85828D]">
            Turn long lectures and tutorials into clear explanations, connected
            concepts, and study material you can actually use.
          </p>

          {/* URL Input */}
          <div className="mt-10 flex w-full max-w-2xl overflow-hidden border border-white/[0.12] bg-[#151519]">
            <input
              type="text"
              placeholder="Paste a YouTube URL"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              className="h-14 flex-1 bg-transparent px-5 text-[15px] text-white outline-none placeholder:text-[#5F5D66] focus:bg-[#18181D]"
            />

            <button
              onClick={handleGenerate}
              className="h-14 bg-[#B08DFF] px-7 text-sm font-semibold text-[#0D0D10] transition hover:bg-[#C2A8FF]"
            >
              Generate
            </button>
          </div>
          {/* Backend Response */}
          {message && <p className="mt-4 text-gray-600">{message}</p>}

          {result && (
            <div className="mx-auto mt-16 grid w-full max-w-[1500px] grid-cols-1 gap-0 text-left lg:grid-cols-[230px_minmax(0,1fr)]">
              <aside className="hidden border-r border-white/[0.08] lg:block">
                <div className="sticky top-24 p-6">
                  <div className="mb-8">
                    <p className="mb-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#5EE7C4]">
                      Workspace
                    </p>

                    <div className="space-y-1 text-sm">
                      <div className="border-l-2 border-[#B08DFF] bg-white/[0.04] px-3 py-2 text-white">
                        Overview
                      </div>

                      <div className="px-3 py-2 text-[#77747E]">Knowledge</div>

                      <div className="px-3 py-2 text-[#77747E]">Study</div>
                    </div>
                  </div>

                  <div>
                    <p className="mb-4 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#5EE7C4]">
                      This video
                    </p>

                    <div className="space-y-1 text-sm text-[#77747E]">
                      <div className="px-3 py-2">Summary</div>
                      <div className="px-3 py-2">Deep Dive</div>
                      <div className="px-3 py-2">Knowledge Graph</div>
                      <div className="px-3 py-2">Study Assets</div>
                      <div className="px-3 py-2">Ask AI</div>
                    </div>
                  </div>
                </div>
              </aside>
              <div className="min-w-0 px-6 py-2 lg:px-12"></div>
              {/* MindBook Header */}
              <div className="border border-white/[0.08] bg-[#121216] p-7">
                <p className="text-sm font-medium text-gray-500">MindBook</p>

                <h2 className="mt-2 text-3xl font-bold text-gray-900">
                  {result.content.overall_topic}
                </h2>

                <div className="mt-4 flex flex-wrap gap-3">
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700">
                    {result.content.content_type}
                  </span>

                  <span className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700">
                    {result.content.difficulty}
                  </span>

                  <span className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700">
                    {result.content.domain}
                  </span>
                </div>
              </div>

              {/* Executive Summary */}
              <div className="rounded-2xl border p-6">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  {" "}
                </h3>

                <p className="mt-3 leading-7 text-gray-600">
                  {result.synthesis.executive_summary}
                </p>
              </div>

              {/* Learning Objectives */}
              <div className="rounded-2xl border p-6">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  🎯 Learning Objectives
                </h3>

                <ul className="mt-4 space-y-3">
                  {result.content.learning_objectives.map(
                    (objective: string, index: number) => (
                      <li key={index} className="flex gap-3">
                        <span>✓</span>
                        <span className="text-gray-600">{objective}</span>
                      </li>
                    )
                  )}
                </ul>
              </div>

              {/* Topics */}
              <div className="rounded-2xl border p-6">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  📚 Topics Covered
                </h3>

                <div className="mt-4 space-y-4">
                  {result.content.topics.map((topic: any, index: number) => (
                    <div key={index} className="rounded-xl bg-gray-50 p-4">
                      <h4 className="font-medium">{topic.title}</h4>

                      <p className="mt-1 text-sm leading-6 text-gray-600">
                        {topic.summary}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Complete Guide */}
              <div className="rounded-2xl border p-6">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  📖 Complete Guide
                </h3>

                <div className="mt-4 whitespace-pre-line leading-7 text-gray-600">
                  {result.synthesis.complete_guide}
                </div>
              </div>

              {/* FAQ */}
              <div className="rounded-2xl border p-6">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  ❓ Frequently Asked Questions
                </h3>

                <div className="mt-4 space-y-5">
                  {result.synthesis.faq.map((item: any, index: number) => (
                    <div key={index}>
                      <h4 className="font-medium">{item.q}</h4>

                      <p className="mt-1 text-sm leading-6 text-gray-600">
                        {item.a}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Knowledge Graph */}
              <div className="border border-white/[0.08] bg-[#121216] p-7">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  🕸️ Knowledge Graph
                </h3>

                {/* Nodes */}
                <div className="mt-6">
                  <h4 className="font-medium text-gray-900">Concepts</h4>

                  <div className="mt-3 flex flex-wrap gap-3">
                    {result.knowledge_graph.nodes.map(
                      (node: any, index: number) => (
                        <span
                          key={index}
                          className="rounded-xl border bg-gray-50 px-4 py-2 text-sm text-gray-700"
                        >
                          {node.label || node.name || node.id}
                        </span>
                      )
                    )}
                  </div>
                </div>

                {/* Relationships */}
                <div className="mt-8">
                  <h4 className="font-medium text-gray-900">Relationships</h4>

                  <div className="mt-3 space-y-3">
                    {result.knowledge_graph.edges.map(
                      (edge: any, index: number) => {
                        const fromNode = result.knowledge_graph.nodes.find(
                          (node: any) => node.id === edge.from
                        );

                        const toNode = result.knowledge_graph.nodes.find(
                          (node: any) => node.id === edge.to
                        );

                        return (
                          <div
                            key={index}
                            className="rounded-xl bg-gray-50 px-4 py-3 text-sm"
                          >
                            <span className="font-medium text-gray-900">
                              {fromNode?.label || edge.from}
                            </span>

                            <span className="mx-2 text-gray-400">→</span>

                            <span className="text-gray-500">
                              {edge.relation}
                            </span>

                            <span className="mx-2 text-gray-400">→</span>

                            <span className="font-medium text-gray-900">
                              {toNode?.label || edge.to}
                            </span>
                          </div>
                        );
                      }
                    )}
                  </div>
                </div>
              </div>

              {/* Deep Dive */}
              <div className="border-t border-[#E5E5E2] pt-10">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  🔍 Deep Dive
                </h3>

                <div className="mt-6 space-y-6">
                  {result.deep_dive.map((chunk: any, index: number) => (
                    <div
                      key={chunk.chunk_id ?? index}
                      className="border-b border-[#E5E5E2] py-12 first:pt-0 last:border-b-0"
                    >
                      {/* Chunk Header */}

                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold">
                          Chunk {chunk.chunk_id}
                        </h4>

                        <span className="rounded-full bg-white px-3 py-1 text-sm">
                          Difficulty: {chunk.result.difficulty_rating}/5
                        </span>
                      </div>
                      {/* Explanation Blocks */}
                      <div className="mt-5 space-y-5">
                        {chunk.result.blocks.map(
                          (block: any, blockIndex: number) => (
                            <div key={blockIndex}>
                              {block.type === "heading" && (
                                <h5 className="font-medium text-gray-900">
                                  {block.content}
                                </h5>
                              )}

                              {block.type === "paragraph" && (
                                <p className="mt-2 leading-7 text-gray-600">
                                  {block.content}
                                </p>
                              )}
                            </div>
                          )
                        )}
                      </div>
                      {/* Key Concepts */}
                      {chunk.result.key_concepts?.length > 0 && (
                        <div className="mt-6">
                          <h5 className="font-medium">💡 Key Concepts</h5>

                          <div className="mt-3 flex flex-wrap gap-2">
                            {chunk.result.key_concepts.map(
                              (concept: string, conceptIndex: number) => (
                                <span
                                  key={conceptIndex}
                                  className="rounded-full bg-white px-3 py-1 text-sm text-gray-700"
                                >
                                  {concept}
                                </span>
                              )
                            )}
                          </div>
                        </div>
                      )}
                      {/* Sketch Note */}
                      {chunk.result.sketch_note && (
                        <div className="mt-6 rounded-xl bg-white p-4">
                          <h5 className="font-medium">
                            📝 {chunk.result.sketch_note.title}
                          </h5>

                          <p className="mt-2 text-sm text-gray-500">
                            {chunk.result.sketch_note.subtitle}
                          </p>

                          <ul className="mt-3 space-y-2">
                            {chunk.result.sketch_note.boxes?.map(
                              (box: string, boxIndex: number) => (
                                <li
                                  key={boxIndex}
                                  className="text-sm text-gray-600"
                                >
                                  • {box}
                                </li>
                              )
                            )}
                          </ul>

                          <p className="mt-4 text-sm leading-6 text-gray-600">
                            <strong>Takeaway:</strong>{" "}
                            {chunk.result.sketch_note.takeaway}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Study Assets */}
              <div className="border border-white/[0.08] bg-[#121216] p-7">
                <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
                  🎯 Study Assets
                </h3>

                {/* Quiz */}
                <div className="mt-6">
                  <h4 className="font-medium text-gray-900">📝 Quiz</h4>

                  <div className="mt-4 space-y-5">
                    {result.study_assets.quiz.map(
                      (question: any, index: number) => {
                        const selected = selectedAnswers[index];
                        const checked = checkedAnswers[index];

                        const isCorrect = selected === question.correct;

                        return (
                          <div
                            key={index}
                            className="rounded-xl bg-gray-50 p-5"
                          >
                            {/* Question */}
                            <div className="flex items-start justify-between gap-4">
                              <h5 className="font-medium">
                                {index + 1}. {question.question}
                              </h5>

                              <span className="shrink-0 rounded-full bg-white px-3 py-1 text-xs">
                                {question.difficulty}
                              </span>
                            </div>

                            {/* Options */}
                            <div className="mt-4 space-y-2">
                              {question.options.map(
                                (option: string, optionIndex: number) => {
                                  const optionLetter = option.split(")")[0];

                                  const isSelected = selected === optionLetter;

                                  return (
                                    <button
                                      key={optionIndex}
                                      onClick={() =>
                                        setSelectedAnswers((prev) => ({
                                          ...prev,
                                          [index]: optionLetter,
                                        }))
                                      }
                                      className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition ${
                                        isSelected
                                          ? "border-black bg-white"
                                          : "border-gray-200 bg-white hover:border-gray-400"
                                      }`}
                                    >
                                      {option}
                                    </button>
                                  );
                                }
                              )}
                            </div>

                            {/* Check Answer */}
                            <button
                              disabled={!selected}
                              onClick={() =>
                                setCheckedAnswers((prev) => ({
                                  ...prev,
                                  [index]: true,
                                }))
                              }
                              className="mt-4 rounded-lg bg-black px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-gray-300"
                            >
                              Check Answer
                            </button>

                            {/* Result */}
                            {checked && (
                              <div className="mt-4 rounded-lg bg-white p-4">
                                <p
                                  className={`font-medium ${
                                    isCorrect
                                      ? "text-green-600"
                                      : "text-red-600"
                                  }`}
                                >
                                  {isCorrect ? "✅ Correct!" : "❌ Wrong!"}
                                </p>

                                {!isCorrect && (
                                  <p className="mt-2 text-sm text-gray-600">
                                    Correct answer:{" "}
                                    <strong>{question.correct}</strong>
                                  </p>
                                )}

                                <p className="mt-2 text-sm leading-6 text-gray-600">
                                  {question.explanation}
                                </p>
                              </div>
                            )}
                          </div>
                        );
                      }
                    )}
                  </div>

                  {/* Reset */}
                  <button
                    onClick={() => {
                      setSelectedAnswers({});
                      setCheckedAnswers({});
                    }}
                    className="mt-6 rounded-lg border px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    Reset Quiz
                  </button>
                </div>

                {/* Concept Timeline */}
                <div className="mt-10">
                  <h4 className="font-medium text-gray-900">
                    ⏱️ Concept Timeline
                  </h4>

                  <div className="mt-4 space-y-3">
                    {result.study_assets.concept_timeline.map(
                      (item: any, index: number) => (
                        <div
                          key={index}
                          className="flex items-center gap-4 rounded-xl bg-gray-50 p-4"
                        >
                          <span className="rounded-lg bg-white px-3 py-2 text-sm font-medium">
                            {item.timestamp}s
                          </span>

                          <div className="flex-1">
                            <p className="font-medium">{item.concept}</p>

                            <p className="text-sm text-gray-500">
                              Importance: {item.importance}
                            </p>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>

                {/* Mind Map */}
                <div className="mt-10">
                  <h4 className="font-medium text-gray-900">🗺️ Mind Map</h4>

                  <div className="mt-4 rounded-xl bg-gray-50 p-6">
                    <div className="space-y-3">
                      {result.study_assets.mind_map_text
                        .split("\n")
                        .map((line: string, index: number) => {
                          const trimmed = line.trim();

                          if (!trimmed) return null;

                          const spaces = line.length - line.trimStart().length;
                          const level = Math.floor(spaces / 2);

                          return (
                            <div
                              key={index}
                              style={{
                                marginLeft: `${level * 32}px`,
                              }}
                              className={`rounded-lg border bg-white px-4 py-3 ${
                                level === 0
                                  ? "text-lg font-bold"
                                  : level === 1
                                  ? "font-semibold"
                                  : "text-sm text-gray-600"
                              }`}
                            >
                              {level > 0 && (
                                <span className="mr-2 text-gray-400">
                                  {level === 1 ? "└─" : "•"}
                                </span>
                              )}

                              {trimmed}
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Features */}
        <section className="grid grid-cols-1 gap-4 pb-10 md:grid-cols-3">
          <div className="rounded-2xl border p-6">
            <h3 className="font-semibold">Smart Summary</h3>

            <p className="mt-2 text-sm text-gray-500">
              Understand the main ideas without watching the entire video.
            </p>
          </div>

          <div className="rounded-2xl border p-6">
            <h3 className="font-semibold">Deep Dive</h3>

            <p className="mt-2 text-sm text-gray-500">
              Explore concepts and explanations extracted from the content.
            </p>
          </div>

          <div className="rounded-2xl border p-6">
            <h3 className="font-semibold">Study Assets</h3>

            <p className="mt-2 text-sm text-gray-500">
              Generate flashcards, quizzes and revision material.
            </p>
          </div>
        </section>

        {/* Ask AI / RAG */}
        <div className="border border-white/[0.08] bg-[#121216] p-7">
          <h3 className="font-serif text-3xl font-normal tracking-tight text-white">
            💬 Ask about this video
          </h3>

          <p className="mt-2 text-sm text-gray-500">
            Ask questions about the concepts explained in this video.
          </p>

          <div className="mt-5 flex gap-3">
            <input
              type="text"
              placeholder="e.g. What is majority voting?"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleAsk();
                }
              }}
              className="flex-1 rounded-xl border border-gray-300 px-5 py-3 outline-none focus:border-black"
            />

            <button
              onClick={handleAsk}
              disabled={asking || !question.trim()}
              className="rounded-xl bg-black px-6 py-3 font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {asking ? "Thinking..." : "Ask"}
            </button>
          </div>

          {askError && <p className="mt-4 text-sm text-red-600">{askError}</p>}

          {answer && (
            <div className="mt-6 rounded-xl bg-gray-50 p-5">
              <h4 className="font-medium">Answer</h4>

              <p className="mt-3 whitespace-pre-line leading-7 text-gray-700">
                {answer}
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
