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

  type Tab = "overview" | "guide" | "deep-dive" | "knowledge" | "study" | "ask";

  const [activeTab, setActiveTab] = useState<Tab>("overview");

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
      setMessage("Your MindBook is ready.");

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
      setMessage("Processing failed.");
    }
  };

  return (
    <main className="min-h-screen bg-[#0B0B0F] text-[#E7E5EA]">
      {/* =========================================================
          TOP NAVIGATION
      ========================================================= */}
      <nav className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#0B0B0F]/95 backdrop-blur-xl">
        <div className="mx-auto flex h-[68px] max-w-[1500px] items-center justify-between px-5 md:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#B08DFF] font-serif text-xl font-semibold text-[#0B0B0F]">
              M
            </div>

            <div>
              <div className="font-serif text-lg tracking-tight text-white">
                MindBook
              </div>

              <div className="hidden text-[9px] uppercase tracking-[0.25em] text-[#66636D] sm:block">
                Learning workspace
              </div>
            </div>
          </div>

          <div className="flex items-center gap-5">
            <div className="hidden items-center gap-2 text-xs text-[#69666F] md:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[#5EE7C4]" />
              AI Study Environment
            </div>

            <button className="border border-white/[0.1] px-4 py-2 text-xs text-[#A7A3AD] transition hover:border-[#B08DFF]/50 hover:text-white">
              My Library
            </button>
          </div>
        </div>
      </nav>

      {/* =========================================================
          LANDING / HERO
      ========================================================= */}
      {!result && (
        <section className="relative flex min-h-[calc(100vh-68px)] items-center justify-center overflow-hidden px-6">
          {/* Ambient glow */}
          <div className="pointer-events-none absolute left-1/2 top-1/3 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-[#7B61FF]/[0.06] blur-[120px]" />

          <div className="relative z-10 w-full max-w-5xl text-center">
            <div className="mb-7 flex justify-center">
              <div className="border border-[#B08DFF]/20 bg-[#B08DFF]/[0.05] px-4 py-2 text-[10px] uppercase tracking-[0.25em] text-[#B08DFF]">
                AI-powered learning workspace
              </div>
            </div>

            <h1 className="mx-auto max-w-4xl font-serif text-5xl font-normal leading-[1.02] tracking-[-0.035em] text-white md:text-7xl lg:text-8xl">
              Learn from videos.
              <br />
              <span className="text-[#B08DFF]">Remember what you learn.</span>
            </h1>

            <p className="mx-auto mt-8 max-w-2xl text-[16px] leading-8 text-[#85818C] md:text-lg">
              Turn long lectures and tutorials into clear explanations,
              connected concepts, deep dives, quizzes, and study material you
              can actually use.
            </p>

            <div className="mx-auto mt-11 flex w-full max-w-2xl overflow-hidden border border-white/[0.12] bg-[#121217] transition focus-within:border-[#B08DFF]/40">
              <input
                type="text"
                placeholder="Paste a YouTube URL..."
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleGenerate();
                  }
                }}
                className="h-14 min-w-0 flex-1 bg-transparent px-5 text-[15px] text-white outline-none placeholder:text-[#55525C]"
              />

              <button
                onClick={handleGenerate}
                className="h-14 bg-[#B08DFF] px-7 text-sm font-semibold text-[#0B0B0F] transition hover:bg-[#C5AEFF]"
              >
                Generate
              </button>
            </div>

            {message && (
              <div className="mt-5 flex items-center justify-center gap-2 text-xs text-[#77737D]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#5EE7C4]" />
                {message}
              </div>
            )}

            <div className="mx-auto mt-16 grid max-w-3xl grid-cols-1 gap-px border border-white/[0.07] bg-white/[0.07] sm:grid-cols-3">
              <div className="bg-[#0F0F13] p-6 text-left">
                <div className="mb-3 text-xs uppercase tracking-[0.18em] text-[#B08DFF]">
                  01
                </div>
                <h3 className="font-serif text-xl text-white">Understand</h3>
                <p className="mt-2 text-xs leading-6 text-[#6F6B75]">
                  Clear summaries and explanations from long videos.
                </p>
              </div>

              <div className="bg-[#0F0F13] p-6 text-left">
                <div className="mb-3 text-xs uppercase tracking-[0.18em] text-[#5EE7C4]">
                  02
                </div>
                <h3 className="font-serif text-xl text-white">Connect</h3>
                <p className="mt-2 text-xs leading-6 text-[#6F6B75]">
                  Discover relationships between important concepts.
                </p>
              </div>

              <div className="bg-[#0F0F13] p-6 text-left">
                <div className="mb-3 text-xs uppercase tracking-[0.18em] text-[#B08DFF]">
                  03
                </div>
                <h3 className="font-serif text-xl text-white">Remember</h3>
                <p className="mt-2 text-xs leading-6 text-[#6F6B75]">
                  Test yourself with quizzes and structured study assets.
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* =========================================================
          RESULT WORKSPACE
      ========================================================= */}
      {result && (
        <div className="mx-auto grid min-h-[calc(100vh-68px)] max-w-[1500px] grid-cols-1 lg:grid-cols-[230px_minmax(0,1fr)]">
          {/* =====================================================
              SIDEBAR
          ===================================================== */}
          <aside className="hidden border-r border-white/[0.07] lg:block">
            <div className="sticky top-[68px] p-5">
              <div className="mb-9">
                <div className="mb-4 px-3 text-[9px] font-semibold uppercase tracking-[0.25em] text-[#5EE7C4]">
                  Workspace
                </div>

                <div className="space-y-1">
                  <a
                    href="#overview"
                    className="block border-l-2 border-[#B08DFF] bg-white/[0.04] px-3 py-2.5 text-xs text-white"
                  >
                    Overview
                  </a>

                  <a
                    href="#knowledge"
                    className="block border-l-2 border-transparent px-3 py-2.5 text-xs text-[#706D77] transition hover:bg-white/[0.03] hover:text-white"
                  >
                    Knowledge
                  </a>

                  <a
                    href="#study"
                    className="block border-l-2 border-transparent px-3 py-2.5 text-xs text-[#706D77] transition hover:bg-white/[0.03] hover:text-white"
                  >
                    Study
                  </a>

                  <a
                    href="#ask"
                    className="block border-l-2 border-transparent px-3 py-2.5 text-xs text-[#706D77] transition hover:bg-white/[0.03] hover:text-white"
                  >
                    Ask AI
                  </a>
                </div>
              </div>

              <div>
                <div className="mb-4 px-3 text-[9px] font-semibold uppercase tracking-[0.25em] text-[#5EE7C4]">
                  This video
                </div>

                <div className="space-y-1">
                  <a
                    href="#summary"
                    className="block px-3 py-2 text-xs text-[#706D77] transition hover:text-white"
                  >
                    Summary
                  </a>

                  <a
                    href="#topics"
                    className="block px-3 py-2 text-xs text-[#706D77] transition hover:text-white"
                  >
                    Topics
                  </a>

                  <a
                    href="#guide"
                    className="block px-3 py-2 text-xs text-[#706D77] transition hover:text-white"
                  >
                    Complete Guide
                  </a>

                  <a
                    href="#deep-dive"
                    className="block px-3 py-2 text-xs text-[#706D77] transition hover:text-white"
                  >
                    Deep Dive
                  </a>

                  <a
                    href="#knowledge"
                    className="block px-3 py-2 text-xs text-[#706D77] transition hover:text-white"
                  >
                    Knowledge Graph
                  </a>

                  <a
                    href="#study"
                    className="block px-3 py-2 text-xs text-[#706D77] transition hover:text-white"
                  >
                    Study Assets
                  </a>
                </div>
              </div>

              <div className="mt-12 border-t border-white/[0.07] pt-5">
                <div className="px-3 text-[9px] uppercase tracking-[0.2em] text-[#4F4C55]">
                  Status
                </div>

                <div className="mt-3 flex items-center gap-2 px-3 text-xs text-[#706D77]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#5EE7C4]" />
                  MindBook ready
                </div>
              </div>
            </div>
          </aside>

          {/* =====================================================
              MAIN CONTENT
          ===================================================== */}
          <div className="min-w-0 px-5 py-8 md:px-8 lg:px-12 lg:py-12">
            {/* =================================================
                VIDEO / TOPIC HEADER
            ================================================= */}
            <section
              id="overview"
              className="border-b border-white/[0.07] pb-10"
            >
              <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-[#77737E]">
                <span>MindBook</span>
                <span className="text-[#403D45]">/</span>
                <span>Generated Study Space</span>
              </div>

              <div className="mt-5 flex flex-col justify-between gap-6 md:flex-row md:items-end">
                <div className="max-w-4xl">
                  <h2 className="font-serif text-4xl font-normal leading-tight tracking-[-0.025em] text-white md:text-6xl">
                    {result.content.overall_topic}
                  </h2>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <span className="border border-[#B08DFF]/20 bg-[#B08DFF]/[0.05] px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-[#B08DFF]">
                      {result.content.content_type}
                    </span>

                    <span className="border border-white/[0.08] px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-[#85818B]">
                      {result.content.difficulty}
                    </span>

                    <span className="border border-white/[0.08] px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-[#85818B]">
                      {result.content.domain}
                    </span>
                  </div>
                </div>

                <div className="hidden text-right md:block">
                  <div className="text-[9px] uppercase tracking-[0.2em] text-[#4F4C55]">
                    Study mode
                  </div>
                  <div className="mt-1 text-xs text-[#77737E]">
                    Deep learning
                  </div>
                </div>
              </div>
            </section>

            {/* TAB NAVIGATION */}
            <div className="sticky top-16 z-30 -mx-2 overflow-x-auto border-b border-[#27272A] bg-[#0B0B0F]/95 px-2 backdrop-blur">
              <div className="flex min-w-max gap-1 py-2">
                {[
                  ["overview", "Overview"],
                  ["guide", "Guide"],
                  ["deep-dive", "Deep Dive"],
                  ["knowledge", "Knowledge"],
                  ["study", "Study"],
                  ["ask", "Ask AI"],
                ].map(([id, label]) => (
                  <button
                    key={id}
                    onClick={() => setActiveTab(id as Tab)}
                    className={`relative rounded-lg px-4 py-2.5 text-sm font-medium transition ${
                      activeTab === id
                        ? "bg-[#B08DFF]/10 text-[#B08DFF]"
                        : "text-[#8B8B95] hover:bg-white/[0.04] hover:text-white"
                    }`}
                  >
                    {label}

                    {activeTab === id && (
                      <span className="absolute inset-x-3 -bottom-2 h-px bg-[#B08DFF]" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* =================================================
                EXECUTIVE SUMMARY
            ================================================= */}
            <section
              id="summary"
              className="border-b border-white/[0.07] py-10"
            >
              <div className="grid gap-8 md:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] text-[#B08DFF]">
                    01 — Summary
                  </div>

                  <h3 className="mt-3 font-serif text-2xl text-white">
                    Executive Summary
                  </h3>
                </div>

                <div>
                  <p className="max-w-4xl text-[16px] leading-8 text-[#A09CA7]">
                    {result.synthesis.executive_summary}
                  </p>
                </div>
              </div>
            </section>

            {/* =================================================
                LEARNING OBJECTIVES
            ================================================= */}
            <section className="border-b border-white/[0.07] py-10">
              <div className="grid gap-8 md:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] text-[#5EE7C4]">
                    Learning
                  </div>

                  <h3 className="mt-3 font-serif text-2xl text-white">
                    Objectives
                  </h3>
                </div>

                <div className="grid gap-px border border-white/[0.07] bg-white/[0.07] md:grid-cols-2">
                  {result.content.learning_objectives.map(
                    (objective: string, index: number) => (
                      <div key={index} className="flex gap-4 bg-[#101014] p-5">
                        <span className="font-mono text-xs text-[#B08DFF]">
                          {String(index + 1).padStart(2, "0")}
                        </span>

                        <span className="text-sm leading-6 text-[#96929C]">
                          {objective}
                        </span>
                      </div>
                    )
                  )}
                </div>
              </div>
            </section>

            {/* =================================================
                TOPICS
            ================================================= */}
            <section id="topics" className="border-b border-white/[0.07] py-10">
              <div className="grid gap-8 md:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] text-[#B08DFF]">
                    02 — Structure
                  </div>

                  <h3 className="mt-3 font-serif text-2xl text-white">
                    Topics Covered
                  </h3>
                </div>

                <div className="space-y-px border border-white/[0.07] bg-white/[0.07]">
                  {result.content.topics.map((topic: any, index: number) => (
                    <div
                      key={index}
                      className="group flex gap-5 bg-[#101014] p-5 transition hover:bg-[#14141A]"
                    >
                      <span className="pt-1 font-mono text-[10px] text-[#5B5761]">
                        {String(index + 1).padStart(2, "0")}
                      </span>

                      <div>
                        <h4 className="font-serif text-xl text-[#E7E5EA] transition group-hover:text-[#B08DFF]">
                          {topic.title}
                        </h4>

                        <p className="mt-2 max-w-3xl text-sm leading-7 text-[#77737D]">
                          {topic.summary}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* =================================================
                COMPLETE GUIDE
            ================================================= */}
            <section id="guide" className="border-b border-white/[0.07] py-12">
              <div className="grid gap-8 md:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] text-[#5EE7C4]">
                    03 — Guide
                  </div>

                  <h3 className="mt-3 font-serif text-2xl text-white">
                    Complete Guide
                  </h3>
                </div>

                <div className="max-w-4xl whitespace-pre-line text-[15px] leading-8 text-[#9D99A3]">
                  {result.synthesis.complete_guide}
                </div>
              </div>
            </section>

            {/* =================================================
                FAQ
            ================================================= */}
            <section className="border-b border-white/[0.07] py-10">
              <div className="grid gap-8 md:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] text-[#B08DFF]">
                    Reference
                  </div>

                  <h3 className="mt-3 font-serif text-2xl text-white">FAQ</h3>
                </div>

                <div className="divide-y divide-white/[0.07] border-y border-white/[0.07]">
                  {result.synthesis.faq.map((item: any, index: number) => (
                    <div key={index} className="py-6">
                      <h4 className="font-serif text-xl text-white">
                        {item.q}
                      </h4>

                      <p className="mt-3 max-w-3xl text-sm leading-7 text-[#77737D]">
                        {item.a}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* =================================================
                KNOWLEDGE GRAPH
            ================================================= */}
            <section
              id="knowledge"
              className="border-b border-white/[0.07] py-12"
            >
              <div className="grid gap-8 md:grid-cols-[180px_minmax(0,1fr)]">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] text-[#5EE7C4]">
                    04 — Knowledge
                  </div>

                  <h3 className="mt-3 font-serif text-2xl text-white">
                    Knowledge Graph
                  </h3>

                  <p className="mt-3 text-xs leading-6 text-[#5E5A64]">
                    Concepts and relationships extracted from the learning
                    material.
                  </p>
                </div>

                <div>
                  <div>
                    <div className="mb-4 text-[9px] uppercase tracking-[0.2em] text-[#65616B]">
                      Concepts
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {result.knowledge_graph.nodes.map(
                        (node: any, index: number) => (
                          <span
                            key={index}
                            className="border border-[#B08DFF]/15 bg-[#B08DFF]/[0.04] px-3 py-2 text-xs text-[#A7A2AE] transition hover:border-[#B08DFF]/40 hover:text-[#D3C5F5]"
                          >
                            {node.label || node.name || node.id}
                          </span>
                        )
                      )}
                    </div>
                  </div>

                  <div className="mt-10">
                    <div className="mb-4 text-[9px] uppercase tracking-[0.2em] text-[#65616B]">
                      Relationships
                    </div>

                    <div className="space-y-2">
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
                              className="flex flex-wrap items-center gap-2 border border-white/[0.07] bg-[#101014] px-4 py-3 text-xs"
                            >
                              <span className="font-medium text-white">
                                {fromNode?.label || edge.from}
                              </span>

                              <span className="text-[#B08DFF]">→</span>

                              <span className="text-[#67636D]">
                                {edge.relation}
                              </span>

                              <span className="text-[#5EE7C4]">→</span>

                              <span className="font-medium text-white">
                                {toNode?.label || edge.to}
                              </span>
                            </div>
                          );
                        }
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* =================================================
                DEEP DIVE
            ================================================= */}
            <section
              id="deep-dive"
              className="border-b border-white/[0.07] py-12"
            >
              <div className="mb-10">
                <div className="text-[9px] uppercase tracking-[0.22em] text-[#B08DFF]">
                  05 — Deep Learning
                </div>

                <h3 className="mt-3 font-serif text-4xl text-white">
                  Deep Dive
                </h3>

                <p className="mt-3 max-w-2xl text-sm leading-7 text-[#706C76]">
                  A detailed walkthrough of the material, organized into
                  connected learning chunks.
                </p>
              </div>

              <div className="space-y-0">
                {result.deep_dive.map((chunk: any, index: number) => (
                  <article
                    key={chunk.chunk_id ?? index}
                    className="border-t border-white/[0.07] py-10 first:border-t-0 first:pt-0"
                  >
                    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                      <div className="flex items-center gap-4">
                        <span className="font-mono text-[10px] text-[#5C5862]">
                          CHAPTER {String(index + 1).padStart(2, "0")}
                        </span>

                        <span className="h-px w-8 bg-white/[0.1]" />

                        <h4 className="font-serif text-2xl text-white">
                          Chunk {chunk.chunk_id}
                        </h4>
                      </div>

                      <span className="w-fit border border-[#B08DFF]/20 bg-[#B08DFF]/[0.04] px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-[#B08DFF]">
                        Difficulty {chunk.result.difficulty_rating}/5
                      </span>
                    </div>

                    {/* Explanation */}
                    <div className="mt-8 max-w-4xl space-y-7">
                      {chunk.result.blocks.map(
                        (block: any, blockIndex: number) => (
                          <div key={blockIndex}>
                            {block.type === "heading" && (
                              <h5 className="font-serif text-2xl text-[#DDD9E1]">
                                {block.content}
                              </h5>
                            )}

                            {block.type === "paragraph" && (
                              <p className="mt-2 text-[15px] leading-8 text-[#96919C]">
                                {block.content}
                              </p>
                            )}
                          </div>
                        )
                      )}
                    </div>

                    {/* Key concepts */}
                    {chunk.result.key_concepts?.length > 0 && (
                      <div className="mt-9 border-l-2 border-[#5EE7C4]/40 pl-5">
                        <div className="mb-3 text-[9px] uppercase tracking-[0.2em] text-[#5EE7C4]">
                          Key Concepts
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {chunk.result.key_concepts.map(
                            (concept: string, conceptIndex: number) => (
                              <span
                                key={conceptIndex}
                                className="border border-white/[0.08] bg-[#111116] px-3 py-2 text-xs text-[#8E8994]"
                              >
                                {concept}
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    )}

                    {/* Sketch note */}
                    {chunk.result.sketch_note && (
                      <div className="mt-9 max-w-3xl border border-white/[0.08] bg-[#101014] p-6">
                        <div className="flex items-start justify-between gap-5">
                          <div>
                            <div className="text-[9px] uppercase tracking-[0.2em] text-[#B08DFF]">
                              Visual Note
                            </div>

                            <h5 className="mt-2 font-serif text-xl text-white">
                              {chunk.result.sketch_note.title}
                            </h5>
                          </div>
                        </div>

                        <p className="mt-2 text-xs text-[#66626C]">
                          {chunk.result.sketch_note.subtitle}
                        </p>

                        <ul className="mt-5 space-y-3">
                          {chunk.result.sketch_note.boxes?.map(
                            (box: string, boxIndex: number) => (
                              <li
                                key={boxIndex}
                                className="flex gap-3 text-sm leading-6 text-[#85808A]"
                              >
                                <span className="text-[#5EE7C4]">—</span>
                                <span>{box}</span>
                              </li>
                            )
                          )}
                        </ul>

                        <div className="mt-6 border-t border-white/[0.07] pt-5">
                          <div className="text-[9px] uppercase tracking-[0.2em] text-[#65616B]">
                            Takeaway
                          </div>

                          <p className="mt-2 text-sm leading-7 text-[#A19CA6]">
                            {chunk.result.sketch_note.takeaway}
                          </p>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>

            {/* =================================================
                STUDY ASSETS
            ================================================= */}
            <section id="study" className="border-b border-white/[0.07] py-12">
              <div className="mb-10">
                <div className="text-[9px] uppercase tracking-[0.22em] text-[#5EE7C4]">
                  06 — Practice
                </div>

                <h3 className="mt-3 font-serif text-4xl text-white">
                  Study Assets
                </h3>

                <p className="mt-3 max-w-2xl text-sm leading-7 text-[#706C76]">
                  Use these assets to revise the material and test your
                  understanding.
                </p>
              </div>

              {/* =================================================
                  QUIZ
              ================================================= */}
              <div className="border border-white/[0.08] bg-[#101014]">
                <div className="border-b border-white/[0.07] p-6 md:p-7">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-[9px] uppercase tracking-[0.2em] text-[#B08DFF]">
                        Practice
                      </div>

                      <h4 className="mt-2 font-serif text-2xl text-white">
                        Knowledge Check
                      </h4>
                    </div>

                    <span className="font-mono text-[10px] text-[#57535D]">
                      {result.study_assets.quiz.length} QUESTIONS
                    </span>
                  </div>
                </div>

                <div className="divide-y divide-white/[0.07]">
                  {result.study_assets.quiz.map(
                    (question: any, index: number) => {
                      const selected = selectedAnswers[index];
                      const checked = checkedAnswers[index];

                      const isCorrect = selected === question.correct;

                      return (
                        <div key={index} className="p-6 md:p-7">
                          <div className="flex items-start justify-between gap-5">
                            <div className="flex gap-4">
                              <span className="font-mono text-xs text-[#5C5862]">
                                Q{String(index + 1).padStart(2, "0")}
                              </span>

                              <h5 className="max-w-3xl text-sm font-medium leading-7 text-[#D8D4DC]">
                                {question.question}
                              </h5>
                            </div>

                            <span className="hidden shrink-0 border border-white/[0.08] px-2 py-1 text-[9px] uppercase tracking-[0.1em] text-[#625E68] sm:block">
                              {question.difficulty}
                            </span>
                          </div>

                          {/* Options */}
                          <div className="mt-6 space-y-2 pl-0 md:pl-8">
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
                                    className={`w-full border px-4 py-3 text-left text-sm transition ${
                                      isSelected
                                        ? "border-[#B08DFF]/60 bg-[#B08DFF]/[0.07] text-[#D8C9FF]"
                                        : "border-white/[0.07] bg-[#0C0C10] text-[#77737D] hover:border-white/[0.16] hover:text-[#B5B0BA]"
                                    }`}
                                  >
                                    {option}
                                  </button>
                                );
                              }
                            )}
                          </div>

                          {/* Check */}
                          <div className="mt-5 pl-0 md:pl-8">
                            <button
                              disabled={!selected}
                              onClick={() =>
                                setCheckedAnswers((prev) => ({
                                  ...prev,
                                  [index]: true,
                                }))
                              }
                              className="border border-[#B08DFF]/30 bg-[#B08DFF]/[0.08] px-4 py-2 text-xs font-medium text-[#BFAAFF] transition hover:bg-[#B08DFF]/[0.14] disabled:cursor-not-allowed disabled:border-white/[0.05] disabled:bg-transparent disabled:text-[#4E4A53]"
                            >
                              Check Answer
                            </button>
                          </div>

                          {/* Result */}
                          {checked && (
                            <div
                              className={`mt-5 border p-5 md:ml-8 ${
                                isCorrect
                                  ? "border-[#5EE7C4]/20 bg-[#5EE7C4]/[0.04]"
                                  : "border-red-400/20 bg-red-400/[0.03]"
                              }`}
                            >
                              <p
                                className={`text-sm font-medium ${
                                  isCorrect ? "text-[#5EE7C4]" : "text-red-300"
                                }`}
                              >
                                {isCorrect ? "Correct answer" : "Not quite"}
                              </p>

                              {!isCorrect && (
                                <p className="mt-2 text-xs text-[#77737D]">
                                  Correct answer:{" "}
                                  <strong className="text-[#B8B3BD]">
                                    {question.correct}
                                  </strong>
                                </p>
                              )}

                              <p className="mt-3 text-sm leading-7 text-[#85808A]">
                                {question.explanation}
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    }
                  )}
                </div>

                <div className="border-t border-white/[0.07] p-6">
                  <button
                    onClick={() => {
                      setSelectedAnswers({});
                      setCheckedAnswers({});
                    }}
                    className="border border-white/[0.08] px-4 py-2 text-xs text-[#77737D] transition hover:border-white/[0.18] hover:text-white"
                  >
                    Reset Quiz
                  </button>
                </div>
              </div>

              {/* =================================================
                  CONCEPT TIMELINE
              ================================================= */}
              <div className="mt-10">
                <div className="mb-5">
                  <div className="text-[9px] uppercase tracking-[0.2em] text-[#5EE7C4]">
                    Revision
                  </div>

                  <h4 className="mt-2 font-serif text-2xl text-white">
                    Concept Timeline
                  </h4>
                </div>

                <div className="border-y border-white/[0.07]">
                  {result.study_assets.concept_timeline.map(
                    (item: any, index: number) => (
                      <div
                        key={index}
                        className="flex items-center gap-5 border-b border-white/[0.06] py-5 last:border-b-0"
                      >
                        <span className="min-w-[70px] font-mono text-xs text-[#B08DFF]">
                          {item.timestamp}s
                        </span>

                        <div className="h-px w-5 bg-white/[0.12]" />

                        <div>
                          <p className="font-serif text-lg text-[#D7D2DA]">
                            {item.concept}
                          </p>

                          <p className="mt-1 text-[10px] uppercase tracking-[0.12em] text-[#5F5B65]">
                            Importance: {item.importance}
                          </p>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>

              {/* =================================================
                  MIND MAP
              ================================================= */}
              <div className="mt-12">
                <div className="mb-5">
                  <div className="text-[9px] uppercase tracking-[0.2em] text-[#B08DFF]">
                    Structure
                  </div>

                  <h4 className="mt-2 font-serif text-2xl text-white">
                    Mind Map
                  </h4>
                </div>

                <div className="border border-white/[0.07] bg-[#101014] p-6">
                  <div className="space-y-2">
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
                              marginLeft: `${level * 28}px`,
                            }}
                            className={`border-l ${
                              level === 0
                                ? "border-[#B08DFF]/40"
                                : "border-white/[0.08]"
                            } bg-[#0C0C10] px-4 py-3 ${
                              level === 0
                                ? "font-serif text-xl text-white"
                                : level === 1
                                ? "text-sm font-medium text-[#AAA5AF]"
                                : "text-xs text-[#77737D]"
                            }`}
                          >
                            {level > 0 && (
                              <span className="mr-2 text-[#5EE7C4]">
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
            </section>

            {/* =================================================
                ASK AI
            ================================================= */}
            <section id="ask" className="py-14">
              <div className="border border-[#5EE7C4]/15 bg-[#0E1514]">
                <div className="border-b border-white/[0.07] p-7 md:p-8">
                  <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
                    <div>
                      <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.22em] text-[#5EE7C4]">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#5EE7C4]" />
                        Retrieval augmented AI
                      </div>

                      <h3 className="mt-3 font-serif text-3xl text-white md:text-4xl">
                        Ask about this video.
                      </h3>

                      <p className="mt-3 max-w-xl text-sm leading-7 text-[#777E7B]">
                        Ask questions about the concepts explained in this
                        video. MindBook retrieves relevant sections before
                        generating the answer.
                      </p>
                    </div>

                    <div className="hidden text-right md:block">
                      <div className="text-[9px] uppercase tracking-[0.2em] text-[#4F5A57]">
                        Grounded answers
                      </div>
                      <div className="mt-1 text-xs text-[#68736F]">
                        Qdrant + LLM
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-7 md:p-8">
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <input
                      type="text"
                      placeholder="Ask something about this video..."
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          handleAsk();
                        }
                      }}
                      className="h-13 min-w-0 flex-1 border border-white/[0.1] bg-[#0A0F0E] px-5 py-3 text-sm text-white outline-none placeholder:text-[#505854] focus:border-[#5EE7C4]/40"
                    />

                    <button
                      onClick={handleAsk}
                      disabled={asking || !question.trim()}
                      className="h-13 border border-[#5EE7C4]/30 bg-[#5EE7C4] px-7 py-3 text-sm font-semibold text-[#08100E] transition hover:bg-[#83F0D5] disabled:cursor-not-allowed disabled:border-white/[0.05] disabled:bg-[#1D2523] disabled:text-[#5A625F]"
                    >
                      {asking ? "Thinking..." : "Ask AI"}
                    </button>
                  </div>

                  {askError && (
                    <p className="mt-4 text-xs text-red-300">{askError}</p>
                  )}

                  {answer && (
                    <div className="mt-7 border border-white/[0.08] bg-[#0A0F0E] p-6">
                      <div className="text-[9px] uppercase tracking-[0.2em] text-[#5EE7C4]">
                        MindBook answer
                      </div>

                      <p className="mt-4 whitespace-pre-line text-sm leading-8 text-[#A4AAA7]">
                        {answer}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </section>

            {/* =================================================
                FOOTER
            ================================================= */}
            <footer className="border-t border-white/[0.07] py-8">
              <div className="flex flex-col justify-between gap-3 text-[10px] uppercase tracking-[0.15em] text-[#4E4A54] sm:flex-row">
                <span>MindBook</span>
                <span>Learn · Connect · Remember</span>
              </div>
            </footer>
          </div>
        </div>
      )}
    </main>
  );
}
