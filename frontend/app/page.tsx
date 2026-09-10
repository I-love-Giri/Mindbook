"use client";

import { useState } from "react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");

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

      setMessage(`Video ID: ${data.video_id}`);
    } catch (error) {
      console.error(error);
      setMessage("Could not connect to FastAPI.");
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
