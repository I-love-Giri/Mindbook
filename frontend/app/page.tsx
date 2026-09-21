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
    <main className="min-h-screen bg-[#F7F7F5] text-zinc-900">
      <div className="flex min-h-screen">
        {/* ================= SIDEBAR ================= */}
        <aside className="hidden w-64 shrink-0 border-r border-zinc-200 bg-white lg:flex lg:flex-col">
          {/* Logo */}
          <div className="flex h-20 items-center px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm">
                ✦
              </div>

              <div>
                <h1 className="text-lg font-semibold tracking-tight">
                  MindBook
                </h1>

                <p className="text-[11px] text-zinc-400">Learn deeper.</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex-1 px-4 py-4">
            <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
              Library
            </p>

            <nav className="mt-3 space-y-1">
              <button className="flex w-full items-center gap-3 rounded-xl bg-violet-50 px-3 py-2.5 text-sm font-medium text-violet-700">
                <span>✦</span>
                Overview
              </button>

              <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-600 transition hover:bg-zinc-50">
                <span>◈</span>
                Knowledge
              </button>

              <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-600 transition hover:bg-zinc-50">
                <span>▤</span>
                Guide
              </button>

              <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-600 transition hover:bg-zinc-50">
                <span>✧</span>
                Study
              </button>

              <button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-600 transition hover:bg-zinc-50">
                <span>◇</span>
                Notes
              </button>
            </nav>

            <div className="my-8 border-t border-zinc-100" />

            <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
              Features
            </p>

            <div className="mt-3 space-y-1">
              <div className="rounded-xl px-3 py-2.5 text-sm text-zinc-500">
                Smart Summary
              </div>

              <div className="rounded-xl px-3 py-2.5 text-sm text-zinc-500">
                Deep Dive
              </div>

              <div className="rounded-xl px-3 py-2.5 text-sm text-zinc-500">
                Study Assets
              </div>
            </div>
          </div>

          {/* Bottom */}
          <div className="border-t border-zinc-100 p-4">
            <div className="rounded-xl bg-zinc-50 p-3">
              <p className="text-xs font-medium text-zinc-700">MindBook AI</p>

              <p className="mt-1 text-[11px] leading-5 text-zinc-400">
                Turn videos into knowledge you can actually remember.
              </p>
            </div>
          </div>
        </aside>

        {/* ================= MAIN AREA ================= */}
        <div className="min-w-0 flex-1">
          {/* ================= HEADER ================= */}
          <header className="sticky top-0 z-20 border-b border-zinc-200/80 bg-[#F7F7F5]/90 backdrop-blur">
            <div className="flex h-20 items-center justify-between px-6 lg:px-10">
              <div className="lg:hidden">
                <h1 className="text-lg font-semibold">MindBook</h1>
              </div>

              <div className="hidden lg:block">
                <p className="text-sm text-zinc-500">
                  Your personal learning workspace
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button className="hidden rounded-xl border border-zinc-200 bg-white px-4 py-2 text-sm text-zinc-600 shadow-sm transition hover:border-zinc-300 hover:text-zinc-900 sm:block">
                  My Library
                </button>

                <div className="flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 bg-white text-sm font-medium shadow-sm">
                  M
                </div>
              </div>
            </div>
          </header>

          {/* ================= PAGE CONTENT ================= */}
          <section className="mx-auto max-w-6xl px-6 py-12 lg:px-10 lg:py-16">
            {/* HERO */}
            <div className="max-w-4xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-700">
                <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                AI-powered learning workspace
              </div>

              <h2 className="mt-6 text-4xl font-semibold tracking-tight text-zinc-950 sm:text-5xl lg:text-6xl">
                Turn videos into
                <span className="block text-violet-600">
                  knowledge you remember.
                </span>
              </h2>

              <p className="mt-6 max-w-2xl text-base leading-7 text-zinc-500 sm:text-lg">
                Paste a YouTube video and MindBook transforms it into structured
                notes, deep explanations, knowledge graphs, quizzes and revision
                material.
              </p>
            </div>

            {/* ================= URL INPUT ================= */}
            <div className="mt-10 max-w-4xl">
              <div className="rounded-2xl border border-zinc-200 bg-white p-2 shadow-[0_8px_30px_rgba(0,0,0,0.04)]">
                <div className="flex flex-col gap-2 sm:flex-row">
                  <div className="flex flex-1 items-center gap-3 px-4">
                    <span className="text-lg text-zinc-400">🔗</span>

                    <input
                      type="text"
                      placeholder="Paste a YouTube URL..."
                      value={url}
                      onChange={(event) => setUrl(event.target.value)}
                      className="min-w-0 flex-1 bg-transparent py-4 text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
                    />
                  </div>

                  <button
                    onClick={handleGenerate}
                    className="rounded-xl bg-violet-600 px-7 py-3.5 text-sm font-medium text-white shadow-sm transition hover:bg-violet-700 active:scale-[0.98]"
                  >
                    Generate MindBook
                    <span className="ml-2">→</span>
                  </button>
                </div>
              </div>

              {message && (
                <div className="mt-3 flex items-center gap-2 px-2 text-sm text-zinc-500">
                  <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                  {message}
                </div>
              )}
            </div>

            {/* ================= WHAT MINDBOOK CREATES ================= */}
            {!result && (
              <div className="mt-20">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">
                    What MindBook creates
                  </p>

                  <h3 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-900">
                    One video. A complete learning system.
                  </h3>
                </div>

                <div className="mt-7 grid gap-4 md:grid-cols-3">
                  {/* Summary */}
                  <div className="group rounded-2xl border border-zinc-200 bg-white p-6 transition duration-200 hover:-translate-y-1 hover:border-violet-200 hover:shadow-[0_12px_35px_rgba(124,58,237,0.08)]">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-50 text-lg text-violet-600">
                      ✦
                    </div>

                    <h4 className="mt-5 font-semibold text-zinc-900">
                      Smart Summary
                    </h4>

                    <p className="mt-2 text-sm leading-6 text-zinc-500">
                      Understand the main ideas without going through the entire
                      video again.
                    </p>
                  </div>

                  {/* Deep Dive */}
                  <div className="group rounded-2xl border border-zinc-200 bg-white p-6 transition duration-200 hover:-translate-y-1 hover:border-violet-200 hover:shadow-[0_12px_35px_rgba(124,58,237,0.08)]">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-50 text-lg text-violet-600">
                      ◈
                    </div>

                    <h4 className="mt-5 font-semibold text-zinc-900">
                      Deep Dive
                    </h4>

                    <p className="mt-2 text-sm leading-6 text-zinc-500">
                      Explore concepts with detailed explanations, examples and
                      connected ideas.
                    </p>
                  </div>

                  {/* Study */}
                  <div className="group rounded-2xl border border-zinc-200 bg-white p-6 transition duration-200 hover:-translate-y-1 hover:border-violet-200 hover:shadow-[0_12px_35px_rgba(124,58,237,0.08)]">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-50 text-lg text-violet-600">
                      ✧
                    </div>

                    <h4 className="mt-5 font-semibold text-zinc-900">
                      Study Assets
                    </h4>

                    <p className="mt-2 text-sm leading-6 text-zinc-500">
                      Test yourself with quizzes, timelines and revision
                      material.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* ====================================================== */}
            {/* KEEP YOUR EXISTING RESULT JSX HERE                     */}
            {/* ====================================================== */}

            {result && (
              <div className="mt-12 w-full space-y-6">
                {/* 
                   IMPORTANT:
                   Yahan tera existing result rendering code
                   temporarily same rahega.
  
                   Next step mein isi section ko properly
                   dashboard/reading UI mein redesign karenge.
                */}

                {/* MindBook Header */}
                <div className="rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
                    MindBook
                  </p>

                  <h2 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-950">
                    {result.content.overall_topic}
                  </h2>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <span className="rounded-full bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-700">
                      {result.content.content_type}
                    </span>

                    <span className="rounded-full bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-600">
                      {result.content.difficulty}
                    </span>

                    <span className="rounded-full bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-600">
                      {result.content.domain}
                    </span>
                  </div>
                </div>

                {/* 
                  DON'T DELETE YOUR OTHER RESULT SECTIONS.
  
                  For this first UI step, move your existing:
                  Executive Summary
                  Learning Objectives
                  Topics
                  Complete Guide
                  FAQ
                  Knowledge Graph
                  Deep Dive
                  Study Assets
                  Ask AI
  
                  below this header.
  
                  We will redesign those individually in Step 2.
                */}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
