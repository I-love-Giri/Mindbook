"use client";

import { useState } from "react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<any>(null);

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
              {/* Header */}
              <div className="rounded-2xl border p-6">
                <p className="text-sm text-gray-500">MindBook</p>

                <h2 className="mt-2 text-3xl font-bold">
                  {result.content.overall_topic}
                </h2>

                <div className="mt-4 flex gap-3">
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-sm">
                    {result.content.content_type}
                  </span>

                  <span className="rounded-full bg-gray-100 px-3 py-1 text-sm">
                    {result.content.difficulty}
                  </span>

                  <span className="rounded-full bg-gray-100 px-3 py-1 text-sm">
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
