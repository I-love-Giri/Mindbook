"use client";

import { useState } from "react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<any>(null);

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

      setMessage("Processing started...");

      checkStatus(data.video_id);
    } catch (error) {
      console.error(error);
      setMessage("Could not connect to FastAPI.");
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
    <main className="min-h-screen bg-white text-gray-900">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6">
        {/* Navbar */}
        <nav className="flex items-center justify-between py-6">
          <h1 className="text-2xl font-bold">MindBook</h1>

          <button className="rounded-lg border px-4 py-2 text-sm hover:bg-gray-50">
            My Library
          </button>
        </nav>

        {/* Hero Section */}
        <section className="flex flex-1 flex-col items-center justify-center text-center">
          <div className="mb-4 rounded-full bg-gray-100 px-4 py-2 text-sm">
            AI-powered learning assistant
          </div>

          <h2 className="max-w-3xl text-5xl font-bold tracking-tight">
            Turn YouTube videos into
            <span className="block">powerful study notes.</span>
          </h2>

          <p className="mt-6 max-w-2xl text-lg text-gray-500">
            Paste a YouTube video and MindBook will transform it into summaries,
            deep explanations, knowledge graphs, flashcards and more.
          </p>

          {/* URL Input */}
          <div className="mt-10 flex w-full max-w-2xl gap-3">
            <input
              type="text"
              placeholder="Paste YouTube URL..."
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              className="flex-1 rounded-xl border border-gray-300 px-5 py-4 outline-none focus:border-black"
            />

            <button
              onClick={handleGenerate}
              className="rounded-xl bg-black px-6 py-4 font-medium text-white hover:bg-gray-800"
            >
              Generate
            </button>
          </div>

          {/* Backend Response */}
          {message && <p className="mt-4 text-gray-600">{message}</p>}

          {result && (
            <div className="mt-12 w-full max-w-5xl text-left space-y-6">
              {/* MindBook Header */}
              <div className="rounded-2xl border bg-white p-6 shadow-sm">
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
                <h3 className="text-xl font-semibold">⚡ Executive Summary</h3>

                <p className="mt-3 leading-7 text-gray-600">
                  {result.synthesis.executive_summary}
                </p>
              </div>

              {/* Learning Objectives */}
              <div className="rounded-2xl border p-6">
                <h3 className="text-xl font-semibold">
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
                <h3 className="text-xl font-semibold">📚 Topics Covered</h3>

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
                <h3 className="text-xl font-semibold">📖 Complete Guide</h3>

                <div className="mt-4 whitespace-pre-line leading-7 text-gray-600">
                  {result.synthesis.complete_guide}
                </div>
              </div>

              {/* FAQ */}
              <div className="rounded-2xl border p-6">
                <h3 className="text-xl font-semibold">
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
              <div className="rounded-2xl border bg-white p-6 shadow-sm">
                <h3 className="text-xl font-semibold">🕸️ Knowledge Graph</h3>

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
              <div className="rounded-2xl border bg-white p-6 shadow-sm">
                <h3 className="text-xl font-semibold">🔍 Deep Dive</h3>

                <div className="mt-6 space-y-6">
                  {result.deep_dive.map((chunk: any, index: number) => (
                    <div
                      key={chunk.chunk_id ?? index}
                      className="rounded-xl bg-gray-50 p-5"
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
              <div className="rounded-2xl border bg-white p-6 shadow-sm">
                <h3 className="text-xl font-semibold">🎯 Study Assets</h3>

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

                  <pre className="mt-4 overflow-x-auto rounded-xl bg-gray-50 p-5 text-sm leading-7 text-gray-700">
                    {result.study_assets.mind_map_text}
                  </pre>
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
      </div>
    </main>
  );
}
