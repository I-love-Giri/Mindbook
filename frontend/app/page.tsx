"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ============================================================
//  TYPES
// ============================================================

type Phase = "idle" | "processing" | "done" | "failed";

type DeepDiveBlock = {
  type: string;
  content: string;
  caption?: string;
  language?: string;
  variant?: string;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MindBookResult = any;

type Tab = "executive" | "deep-dive" | "knowledge" | "guide" | "study" | "ask";

// ============================================================
//  STAGES (Human, honest, product-focused)
// ============================================================

const STAGES = [
  {
    label: "Reading the video transcript",
    detail: "Extracting spoken content, timestamps, and structure",
  },
  {
    label: "Finding the foundational ideas",
    detail: "Isolating key arguments and learning objectives",
  },
  {
    label: "Connecting related concepts",
    detail: "Building concept graph and relationship dependencies",
  },
  {
    label: "Writing deep explanations",
    detail: "Drafting chunk-by-chunk breakdowns and visual notes",
  },
  {
    label: "Preparing your study material",
    detail: "Formulating recall questions, timeline, and summary",
  },
];

const TABS: { id: Tab; label: string; number: string }[] = [
  { id: "executive", label: "The Big Picture", number: "01" },
  { id: "deep-dive", label: "Deep Dive", number: "02" },
  { id: "knowledge", label: "Concept Map", number: "03" },
  { id: "guide", label: "Complete Guide", number: "04" },
  { id: "study", label: "Study & Quiz", number: "05" },
  { id: "ask", label: "Ask a Question", number: "06" },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ============================================================
//  CODE BLOCK WITH COPY ACTION
// ============================================================

function CodeSnippet({
  code,
  language,
  caption,
}: {
  code: string;
  language?: string;
  caption?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full my-6 overflow-hidden rounded-lg border border-[var(--border)] bg-[#111214]">
      <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-2.5 text-xs text-[var(--text-tertiary)]">
        <span className="font-mono text-[11px] text-[var(--text-secondary)]">
          {caption || language || "snippet"}
        </span>
        <button
          onClick={handleCopy}
          className="btn-press font-mono text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-[13px] font-mono leading-6 text-zinc-300">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// ============================================================
//  RICH BLOCK RENDERER (Editorial reader, not dashboard boxes)
// ============================================================

function RichBlock({ block }: { block: DeepDiveBlock }) {
  if (block.type === "heading") {
    return (
      <h3 className="font-serif text-2xl font-normal tracking-tight text-[var(--text-primary)] mt-10 mb-4 first:mt-0">
        {block.content}
      </h3>
    );
  }

  if (block.type === "paragraph") {
    return <p className="prose-editorial mb-5">{block.content}</p>;
  }

  if (block.type === "code") {
    return (
      <CodeSnippet
        code={block.content}
        language={block.language}
        caption={block.caption}
      />
    );
  }

  if (block.type === "table") {
    const rows = String(block.content || "")
      .split("\n")
      .filter((row: string) => row.trim() && !/^\s*\|?\s*:?-+/.test(row));

    const cells = (row: string) =>
      row
        .split("|")
        .map((cell) => cell.trim())
        .filter(Boolean);

    const [head, ...body] = rows.map(cells);

    return (
      <div className="w-full my-6 overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="w-full min-w-[480px] text-left text-sm">
          <thead className="border-b border-[var(--border)] bg-white/[0.02] text-[var(--text-primary)] font-medium">
            <tr>
              {head?.map((cell: string, index: number) => (
                <th
                  className="px-4 py-3 text-xs font-mono text-[var(--text-secondary)] uppercase tracking-wider"
                  key={index}
                >
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)] text-[var(--text-secondary)]">
            {body.map((row: string[], rowIndex: number) => (
              <tr
                key={rowIndex}
                className="hover:bg-white/[0.015] transition-colors"
              >
                {row.map((cell, cellIndex) => (
                  <td
                    className="px-4 py-3 text-sm leading-relaxed"
                    key={cellIndex}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (block.type === "ascii_diagram") {
    return (
      <div className="my-6 overflow-x-auto rounded-lg border border-[var(--border)] bg-[#101114] p-5">
        <pre className="font-mono text-xs leading-6 text-zinc-300">
          {block.content}
        </pre>
      </div>
    );
  }

  if (block.type === "callout") {
    return (
      <div className="my-6 border-l-2 border-[var(--accent)] bg-[var(--accent-subtle)] px-5 py-4 rounded-r-lg">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--accent)] font-medium">
          {block.variant || "Key Note"}
        </span>
        <p className="mt-1 text-sm leading-relaxed text-[var(--text-secondary)]">
          {block.content}
        </p>
      </div>
    );
  }

  return null;
}

// ============================================================
//  MAIN COMPONENT
// ============================================================

export default function Home() {
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<MindBookResult | null>(null);
  const [videoId, setVideoId] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [stageIndex, setStageIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<Tab>("executive");

  const [selectedAnswers, setSelectedAnswers] = useState<{
    [key: number]: string;
  }>({});
  const [checkedAnswers, setCheckedAnswers] = useState<{
    [key: number]: boolean;
  }>({});

  // hero typing effect
  const [heroReady, setHeroReady] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setHeroReady(true), 200);
    return () => clearTimeout(t);
  }, []);

  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  // Preset example links for easy testing
  const sampleVideos = [
    {
      title: "3Blue1Brown · Neural Networks",
      url: "https://www.youtube.com/watch?v=aircAruvnKk",
    },
    {
      title: "Veritasium · How Transistors Work",
      url: "https://www.youtube.com/watch?v=IcrBqCFLHIY",
    },
    {
      title: "MIT OpenCourseWare · Dynamic Programming",
      url: "https://www.youtube.com/watch?v=OQ5jsbhAv_M",
    },
  ];

  // ============================================================
  //  API HANDLERS (Identical preserved logic)
  // ============================================================

  const handleGenerate = useCallback(
    async (customUrl?: string) => {
      const targetUrl = customUrl || url;
      if (!targetUrl.trim()) {
        setMessage("Please enter a YouTube video URL.");
        return;
      }

      setMessage("");
      setResult(null);
      setStageIndex(0);
      setPhase("processing");

      try {
        const response = await fetch(`${API_URL}/process/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: targetUrl }),
        });

        if (!response.ok) throw new Error("Request failed");
        if (!response.body) throw new Error("Streaming is not available.");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          buffer = events.pop() || "";

          for (const event of events) {
            const line = event
              .split("\n")
              .find((item) => item.startsWith("data: "));

            if (!line) continue;

            const eventData = JSON.parse(line.slice(6));

            if (eventData.message) setMessage(eventData.message);

            if (typeof eventData.stage === "number") {
              setStageIndex(eventData.stage);
            }

            if (eventData.type === "error") throw new Error(eventData.message);

            if (eventData.type === "content") {
              setResult({
                video_id: "",
                content: {
                  learning_objectives: [],
                  topics: [],
                  ...eventData.content,
                },
                knowledge_graph: { nodes: [], edges: [] },
                deep_dive: [],
                synthesis: {
                  executive_summary: "",
                  complete_guide: "",
                  faq: [],
                },
                study_assets: {
                  quiz: [],
                  concept_timeline: [],
                  mind_map_text: "",
                },
              });
            }

            if (eventData.type === "knowledge_graph") {
              setResult((c: MindBookResult | null) =>
                c ? { ...c, knowledge_graph: eventData.knowledge_graph } : c
              );
            }

            if (eventData.type === "deep_dive_section") {
              setResult((c: MindBookResult | null) => {
                if (!c) return c;
                const dd = [...(c?.deep_dive || [])];
                dd[eventData.section_index] = eventData.section;
                return { ...c, deep_dive: dd.filter(Boolean) };
              });
            }

            if (eventData.type === "synthesis") {
              setResult((c: MindBookResult | null) =>
                c ? { ...c, synthesis: eventData.synthesis } : c
              );
            }

            if (eventData.type === "complete") {
              setVideoId(eventData.result.video_id);
              setResult(eventData.result);
              setStageIndex(STAGES.length - 1);
              setPhase("done");
            }
          }
        }
      } catch (error) {
        console.error(error);
        setResult(null);
        setMessage("Could not connect to the processing server.");
        setPhase("failed");
      }
    },
    [url]
  );

  const handleAsk = useCallback(async () => {
    if (!question.trim()) return;
    if (!videoId) {
      setAskError("Please generate a study guide first.");
      return;
    }

    setAsking(true);
    setAnswer("");
    setAskError("");

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: videoId, question }),
      });

      if (!response.ok) throw new Error("Failed to get answer");

      const data = await response.json();
      setAnswer(data.answer);
    } catch (error) {
      console.error(error);
      setAskError("Could not retrieve an answer. Please try again.");
    } finally {
      setAsking(false);
    }
  }, [question, videoId]);

  const goToTab = (id: Tab) => {
    setActiveTab(id);
    document
      .getElementById(id)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const resetMindBook = () => {
    setPhase("idle");
    setResult(null);
    setUrl("");
    setMessage("");
    setVideoId("");
    setQuestion("");
    setAnswer("");
    setSelectedAnswers({});
    setCheckedAnswers({});
  };

  // Progress percentage calculation
  const progressPercent = Math.min(
    100,
    Math.round(((stageIndex + 1) / STAGES.length) * 100)
  );

  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
      {/* ==============================================================
          NAVBAR: Minimal, understated (Linear style)
      ============================================================== */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 border-b ${
          scrolled || phase === "done"
            ? "border-[var(--border)] bg-[#0c0d0e]/90 backdrop-blur-md"
            : "border-transparent bg-transparent"
        }`}
      >
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="font-semibold text-sm tracking-tight text-[var(--text-primary)]">
              MindBook
            </span>
            <span className="text-[var(--text-muted)] text-xs">·</span>
            <span className="text-xs text-[var(--text-tertiary)] hidden sm:inline">
              Your learning workspace
            </span>
          </div>

          <div className="flex items-center gap-3">
            {phase === "done" && (
              <button
                onClick={resetMindBook}
                className="btn-press flex items-center gap-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] px-3 py-1.5 rounded-md border border-[var(--border)] bg-white/[0.02]"
              >
                <span>←</span>
                <span>New guide</span>
              </button>
            )}

            {phase === "processing" && (
              <div className="flex items-center gap-2 text-xs text-[var(--text-tertiary)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
                <span>Processing video</span>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* ==============================================================
          HERO & INPUT (Quiet, Editorial, Linear-style command input)
      ============================================================== */}
      {phase !== "done" && !result && (
        <section className="relative flex min-h-[92vh] flex-col items-center justify-center px-4 pt-20 pb-16 overflow-hidden">
          <div className="hero-ambient" />
          <div className="hero-subtle-grid" />

          <div className="relative z-10 mx-auto w-full max-w-2xl text-center">
            {/* Tagline kicker */}
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="font-mono text-[11px] uppercase tracking-[0.25em] text-[var(--text-muted)] mb-4"
            >
              Editorial Study System
            </motion.p>

            {/* Headline: Human, thoughtful, quiet */}
            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={heroReady ? { opacity: 1, y: 0 } : {}}
              transition={{
                duration: 0.9,
                delay: 0.1,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="font-serif text-5xl font-normal leading-[1.05] tracking-[-0.03em] text-[var(--text-primary)] sm:text-6xl md:text-7xl lg:text-[5.5rem]"
            >
              Not a Summary.
              <br />
              <span className="bg-gradient-to-r from-[var(--accent)] to-[var(--mint)] bg-clip-text text-transparent">
                Deep Intelligence.
              </span>
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.16 }}
              className="mx-auto mt-5 max-w-lg text-sm sm:text-base leading-relaxed text-[var(--text-secondary)]"
            >
              Paste any lecture, talk, or tutorial. MindBook reads the full
              transcript, isolates core arguments, and crafts a structured study
              guide for lasting retention.
            </motion.p>

            {/* Input Form or Loading state */}
            {phase === "idle" || phase === "failed" ? (
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="mt-8 sm:mt-10"
              >
                {/* Input */}
                <div className="group relative">
                  {/* Focus glow */}
                  <div className="pointer-events-none absolute -inset-[1px] rounded-2xl bg-gradient-to-r from-white/[0.08] via-white/[0.02] to-white/[0.08] opacity-0 blur-sm transition-opacity duration-300 group-focus-within:opacity-100" />

                  <div
                    className="
          relative flex items-center gap-2
          rounded-2xl
          border border-white/[0.08]
          bg-white/[0.035]
          p-1.5
          shadow-[0_8px_30px_rgba(0,0,0,0.18)]
          backdrop-blur-xl
          transition-all duration-300
          group-focus-within:border-white/[0.14]
          group-focus-within:bg-white/[0.045]
        "
                  >
                    {/* Link icon */}
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center text-zinc-500 transition-colors duration-200 group-focus-within:text-zinc-300">
                      <svg
                        className="h-[17px] w-[17px]"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.7"
                      >
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                      </svg>
                    </div>

                    {/* Input */}
                    <input
                      type="text"
                      placeholder="Paste a YouTube link..."
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleGenerate();
                      }}
                      className="
            h-11 min-w-0 flex-1
            bg-transparent
            px-1
            text-sm
            text-[var(--text-primary)]
            outline-none
            placeholder:text-zinc-600
          "
                    />

                    {/* Generate button */}
                    <button
                      onClick={() => handleGenerate()}
                      className="
    btn-press
    flex h-11 shrink-0 items-center gap-2
    rounded-xl
    bg-white
    px-4 sm:px-5
    text-xs font-semibold
    text-zinc-950
    shadow-sm
    transition-all duration-200
    hover:bg-zinc-100
    hover:shadow-[0_4px_18px_rgba(255,255,255,0.08)]
    active:scale-[0.98]
  "
                    >
                      <span>Generate</span>

                      <svg
                        className="h-3.5 w-3.5"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                      >
                        <path
                          d="M3 8h9M8.5 4.5L12 8l-3.5 3.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Status / Error message */}
                {message && (
                  <motion.p
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`mt-3 px-1 text-xs ${
                      phase === "failed"
                        ? "text-[var(--error)]"
                        : "text-[var(--text-tertiary)]"
                    }`}
                  >
                    {message}
                  </motion.p>
                )}

                {/* Example links */}
                {!message && (
                  <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
                    <span className="mr-1 text-[11px] text-zinc-600">
                      Try an example
                    </span>

                    {sampleVideos.map((sample) => (
                      <button
                        key={sample.title}
                        onClick={() => {
                          setUrl(sample.url);
                          handleGenerate(sample.url);
                        }}
                        className="
              rounded-full
              border border-white/[0.07]
              bg-white/[0.025]
              px-3 py-1.5
              text-[11px]
              text-zinc-500
              transition-all duration-200
              hover:border-white/[0.14]
              hover:bg-white/[0.06]
              hover:text-zinc-200
              active:scale-95
            "
                      >
                        {sample.title}
                      </button>
                    ))}
                  </div>
                )}
              </motion.div>
            ) : (
              /* ==============================================================
                  HUMAN LOADING EXPERIENCE (Checklist style, product-focused)
              ============================================================== */
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="mx-auto mt-10 w-full max-w-md text-left"
              >
                <div className="rounded-xl border border-[var(--border)] bg-[#131416] p-6">
                  <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
                    <span className="font-serif text-lg text-[var(--text-primary)]">
                      Creating your study guide
                    </span>
                    <span className="font-mono text-xs text-[var(--text-secondary)]">
                      {progressPercent}%
                    </span>
                  </div>

                  {/* Progress Line */}
                  <div className="my-5 h-[2px] w-full overflow-hidden rounded-full bg-white/[0.06]">
                    <motion.div
                      className="h-full bg-[var(--accent)]"
                      initial={{ width: 0 }}
                      animate={{ width: `${progressPercent}%` }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                    />
                  </div>

                  {/* Step Checklist */}
                  <div className="space-y-3.5 pt-1">
                    {STAGES.map((stage, i) => {
                      const isDone = i < stageIndex;
                      const isActive = i === stageIndex;

                      return (
                        <div
                          key={stage.label}
                          className="flex items-start gap-3"
                        >
                          <span className="mt-0.5 font-mono text-xs shrink-0 w-4 text-center">
                            {isDone ? (
                              <span className="text-[var(--success)]">✓</span>
                            ) : isActive ? (
                              <span className="text-[var(--accent)] animate-pulse">
                                ●
                              </span>
                            ) : (
                              <span className="text-[var(--text-muted)]">
                                ○
                              </span>
                            )}
                          </span>

                          <div className="min-w-0">
                            <p
                              className={`text-xs ${
                                isDone
                                  ? "text-[var(--text-secondary)]"
                                  : isActive
                                  ? "text-[var(--text-primary)] font-medium"
                                  : "text-[var(--text-muted)]"
                              }`}
                            >
                              {stage.label}
                            </p>
                            {isActive && (
                              <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
                                {stage.detail}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </section>
      )}

      {/* ==============================================================
          RESULT PAGE: Premium Digital Book / Editorial Reader
      ============================================================== */}
      {(phase === "done" || phase === "processing") && result && (
        <div className="mx-auto min-h-screen max-w-6xl pt-14">
          <div className="grid grid-cols-1 lg:grid-cols-[220px_minmax(0,1fr)] gap-8 px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
            {/* ====== NOTION / LINEAR STYLE SIDEBAR ====== */}
            <aside className="hidden lg:block">
              <div className="sticky top-20">
                <div className="mb-6 pb-4 border-b border-[var(--border)]">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)] block mb-1">
                    Document
                  </span>
                  <p className="text-xs text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
                    {result.content?.overall_topic || "Study Guide"}
                  </p>
                </div>

                <div className="space-y-0.5">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)] block px-3 mb-2">
                    Contents
                  </span>
                  {TABS.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => goToTab(tab.id)}
                      className={`toc-link ${
                        activeTab === tab.id ? "toc-link--active" : ""
                      }`}
                    >
                      <span className="truncate">{tab.label}</span>
                      <span className="font-mono text-[10px] text-[var(--text-muted)]">
                        {tab.number}
                      </span>
                    </button>
                  ))}
                </div>

                <div className="mt-8 pt-4 border-t border-[var(--border)] text-xs text-[var(--text-muted)]">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        phase === "done"
                          ? "bg-[var(--success)]"
                          : "bg-[var(--accent)] animate-pulse"
                      }`}
                    />
                    <span>
                      {phase === "done" ? "Guide completed" : "Reading…"}
                    </span>
                  </div>
                </div>
              </div>
            </aside>

            {/* ====== MAIN EDITORIAL CANVAS ====== */}
            <article className="min-w-0 max-w-3xl">
              {/* ====== CHAPTER TITLE & METADATA ====== */}
              <header className="pb-10 border-b border-[var(--border)]">
                <div className="flex items-center gap-2 font-mono text-xs text-[var(--text-muted)] mb-3">
                  <span>MindBook</span>
                  <span>/</span>
                  <span className="uppercase tracking-wider">Lesson Guide</span>
                </div>

                <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-normal leading-[1.18] tracking-[-0.02em] text-[var(--text-primary)]">
                  {result.content?.overall_topic}
                </h1>

                <div className="mt-5 flex flex-wrap items-center gap-2">
                  {result.content?.content_type && (
                    <span className="tag-mono tag-mono--accent">
                      {result.content.content_type}
                    </span>
                  )}
                  {result.content?.difficulty && (
                    <span className="tag-mono">
                      Level: {result.content.difficulty}
                    </span>
                  )}
                  {result.content?.domain && (
                    <span className="tag-mono">
                      Domain: {result.content.domain}
                    </span>
                  )}
                </div>

                {result.content?.thumbnail && (
                  <div className="mt-8 overflow-hidden rounded-lg border border-[var(--border)]">
                    <img
                      src={result.content.thumbnail}
                      alt={result.content.overall_topic}
                      className="w-full aspect-video object-cover"
                    />
                  </div>
                )}
              </header>

              {/* ====== SECTION 1: THE BIG PICTURE ====== */}
              <section
                id="executive"
                className="py-12 border-b border-[var(--border)] scroll-mt-20"
              >
                <span className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--text-muted)] block mb-4">
                  01 · The Big Picture
                </span>

                <div className="font-serif text-xl sm:text-2xl leading-relaxed text-[var(--text-primary)] font-normal mb-10">
                  {result.synthesis?.executive_summary}
                </div>

                {/* Learning Objectives: Clean numbered list (No cards!) */}
                {result.content?.learning_objectives?.length > 0 && (
                  <div className="mt-10 pt-8 border-t border-[var(--border)]">
                    <h2 className="font-mono text-xs uppercase tracking-[0.15em] text-[var(--text-tertiary)] mb-6">
                      You'll understand
                    </h2>

                    <div className="space-y-4">
                      {result.content.learning_objectives.map(
                        (obj: string, i: number) => (
                          <div key={i} className="flex items-start gap-4">
                            <span className="font-mono text-xs text-[var(--accent)] mt-0.5 min-w-[20px]">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <p className="text-sm sm:text-base leading-relaxed text-[var(--text-secondary)]">
                              {obj}
                            </p>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}

                {/* Core Topics covered */}
                {result.content?.topics?.length > 0 && (
                  <div className="mt-12 pt-8 border-t border-[var(--border)]">
                    <h2 className="font-mono text-xs uppercase tracking-[0.15em] text-[var(--text-tertiary)] mb-6">
                      Topics covered in this lesson
                    </h2>

                    <div className="space-y-6">
                      {result.content.topics.map((topic: any, i: number) => (
                        <div key={i} className="group">
                          <div className="flex items-baseline gap-3">
                            <span className="font-mono text-xs text-[var(--text-muted)]">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <h3 className="text-base font-medium text-[var(--text-primary)]">
                              {topic.title}
                            </h3>
                          </div>
                          <p className="mt-1.5 pl-7 text-sm leading-relaxed text-[var(--text-secondary)]">
                            {topic.summary}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Frequently Asked Questions */}
                {result.synthesis?.faq?.length > 0 && (
                  <div className="mt-12 pt-8 border-t border-[var(--border)]">
                    <h2 className="font-mono text-xs uppercase tracking-[0.15em] text-[var(--text-tertiary)] mb-6">
                      Frequently asked
                    </h2>

                    <div className="space-y-6">
                      {result.synthesis.faq.map((item: any, i: number) => (
                        <div key={i}>
                          <h4 className="text-sm sm:text-base font-medium text-[var(--text-primary)]">
                            {item.q}
                          </h4>
                          <p className="mt-1.5 text-sm leading-relaxed text-[var(--text-secondary)]">
                            {item.a}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              {/* ====== SECTION 2: DEEP DIVE (Chapter-by-Chapter) ====== */}
              <section
                id="deep-dive"
                className="py-12 border-b border-[var(--border)] scroll-mt-20"
              >
                <span className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--text-muted)] block mb-2">
                  02 · Deep Dive
                </span>

                <h2 className="font-serif text-3xl font-normal text-[var(--text-primary)]">
                  Detailed Breakdown
                </h2>

                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  Chapter-by-chapter conceptual walkthrough.
                </p>

                <div className="mt-10 space-y-16">
                  {result.deep_dive?.map((chunk: any, i: number) => (
                    <div
                      key={chunk.chunk_id ?? i}
                      className="pt-8 first:pt-0 border-t border-[var(--border)] first:border-0"
                    >
                      <div className="flex items-center justify-between font-mono text-xs text-[var(--text-muted)] mb-3">
                        <span className="uppercase tracking-wider">
                          Chapter {String(i + 1).padStart(2, "0")}
                        </span>
                        {chunk.result?.difficulty_rating && (
                          <span>
                            Difficulty {chunk.result.difficulty_rating}/5
                          </span>
                        )}
                      </div>

                      {/* Blocks rendered naturally, not trapped in cards */}
                      <div className="mt-4">
                        {chunk.result?.blocks?.map((block: any, bi: number) => (
                          <RichBlock key={bi} block={block} />
                        ))}
                      </div>

                      {/* Key concepts */}
                      {chunk.result?.key_concepts?.length > 0 && (
                        <div className="mt-8 pt-4">
                          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)] block mb-2">
                            Key concepts
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {chunk.result.key_concepts.map(
                              (c: string, ci: number) => (
                                <span key={ci} className="tag-mono">
                                  {c}
                                </span>
                              )
                            )}
                          </div>
                        </div>
                      )}

                      {/* Sketch note / Visual Note */}
                      {chunk.result?.sketch_note && (
                        <div className="mt-8 rounded-lg border border-[var(--border)] bg-[#121316] p-5">
                          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--accent)] font-medium">
                            Visual Note
                          </span>
                          <h4 className="font-serif text-lg text-[var(--text-primary)] mt-1">
                            {chunk.result.sketch_note.title}
                          </h4>
                          {chunk.result.sketch_note.subtitle && (
                            <p className="text-xs text-[var(--text-tertiary)] mt-0.5">
                              {chunk.result.sketch_note.subtitle}
                            </p>
                          )}

                          <ul className="mt-4 space-y-2 text-sm text-[var(--text-secondary)]">
                            {chunk.result.sketch_note.boxes?.map(
                              (box: string, bi: number) => (
                                <li key={bi} className="flex gap-2">
                                  <span className="text-[var(--text-muted)]">
                                    —
                                  </span>
                                  <span>{box}</span>
                                </li>
                              )
                            )}
                          </ul>

                          {chunk.result.sketch_note.takeaway && (
                            <div className="mt-4 pt-3 border-t border-[var(--border)] text-xs text-[var(--text-secondary)]">
                              <strong className="text-[var(--text-primary)] font-medium">
                                Takeaway:{" "}
                              </strong>
                              {chunk.result.sketch_note.takeaway}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>

              {/* ====== SECTION 3: CONCEPT MAP ====== */}
              <section
                id="knowledge"
                className="py-12 border-b border-[var(--border)] scroll-mt-20"
              >
                <span className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--text-muted)] block mb-2">
                  03 · Concept Map
                </span>

                <h2 className="font-serif text-3xl font-normal text-[var(--text-primary)]">
                  Concepts & Relationships
                </h2>

                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  How ideas in this material link to each other.
                </p>

                {/* Nodes */}
                {result.knowledge_graph?.nodes?.length > 0 && (
                  <div className="mt-8">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)] block mb-3">
                      Core Concepts
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {result.knowledge_graph.nodes.map(
                        (node: any, i: number) => (
                          <span
                            key={i}
                            className="tag-mono tag-mono--accent text-xs py-1 px-2.5"
                          >
                            {node.label || node.name || node.id}
                          </span>
                        )
                      )}
                    </div>
                  </div>
                )}

                {/* Edges / Connections */}
                {result.knowledge_graph?.edges?.length > 0 && (
                  <div className="mt-8">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--text-muted)] block mb-3">
                      Relationships
                    </span>
                    <div className="space-y-2">
                      {result.knowledge_graph.edges.map(
                        (edge: any, i: number) => {
                          const from = result.knowledge_graph.nodes?.find(
                            (n: any) => n.id === edge.from
                          );
                          const to = result.knowledge_graph.nodes?.find(
                            (n: any) => n.id === edge.to
                          );

                          return (
                            <div
                              key={i}
                              className="flex flex-wrap items-center gap-2 text-xs py-2 px-3 rounded-md bg-white/[0.02] border border-[var(--border-subtle)]"
                            >
                              <span className="font-medium text-[var(--text-primary)]">
                                {from?.label || edge.from}
                              </span>
                              <span className="text-[var(--text-muted)] font-mono">
                                ──
                              </span>
                              <span className="font-mono text-[11px] text-[var(--accent)]">
                                {edge.relation}
                              </span>
                              <span className="text-[var(--text-muted)] font-mono">
                                ──&gt;
                              </span>
                              <span className="font-medium text-[var(--text-primary)]">
                                {to?.label || edge.to}
                              </span>
                            </div>
                          );
                        }
                      )}
                    </div>
                  </div>
                )}
              </section>

              {/* ====== SECTION 4: COMPLETE GUIDE ====== */}
              <section
                id="guide"
                className="py-12 border-b border-[var(--border)] scroll-mt-20"
              >
                <span className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--text-muted)] block mb-2">
                  04 · Complete Guide
                </span>

                <h2 className="font-serif text-3xl font-normal text-[var(--text-primary)]">
                  Full Walkthrough
                </h2>

                <div className="mt-8 prose-editorial whitespace-pre-line leading-relaxed">
                  {result.synthesis?.complete_guide}
                </div>
              </section>

              {/* ====== SECTION 5: STUDY & QUIZ (Interactive) ====== */}
              <section
                id="study"
                className="py-12 border-b border-[var(--border)] scroll-mt-20"
              >
                <span className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--text-muted)] block mb-2">
                  05 · Study & Active Recall
                </span>

                <h2 className="font-serif text-3xl font-normal text-[var(--text-primary)]">
                  Test Your Understanding
                </h2>

                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  Active recall questions and review timeline to cement what
                  you've learned.
                </p>

                {/* Quiz items */}
                {result.study_assets?.quiz?.length > 0 && (
                  <div className="mt-8 space-y-8">
                    {result.study_assets.quiz.map((q: any, i: number) => {
                      const selected = selectedAnswers[i];
                      const checked = checkedAnswers[i];
                      const isCorrect = selected === q.correct;

                      return (
                        <div key={i} className="editorial-card p-5 sm:p-6">
                          <div className="flex items-start gap-3">
                            <span className="font-mono text-xs text-[var(--accent)] mt-0.5">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <h4 className="text-sm sm:text-base font-medium text-[var(--text-primary)] leading-snug">
                              {q.question}
                            </h4>
                          </div>

                          <div className="mt-4 space-y-2 sm:pl-7">
                            {q.options?.map((opt: string, oi: number) => {
                              const letter = opt.split(")")[0]?.trim();
                              const isSelected = selected === letter;
                              const showCorrect =
                                checked && letter === q.correct;
                              const showWrong =
                                checked && isSelected && !isCorrect;

                              return (
                                <button
                                  key={oi}
                                  onClick={() =>
                                    setSelectedAnswers((p) => ({
                                      ...p,
                                      [i]: letter,
                                    }))
                                  }
                                  className={`quiz-option ${
                                    isSelected && !checked
                                      ? "quiz-option--selected"
                                      : ""
                                  } ${
                                    showCorrect ? "quiz-option--correct" : ""
                                  } ${showWrong ? "quiz-option--wrong" : ""}`}
                                  disabled={!!checked}
                                >
                                  <span className="font-mono text-xs text-[var(--text-muted)] min-w-[16px]">
                                    {letter}
                                  </span>
                                  <span>{opt}</span>
                                </button>
                              );
                            })}
                          </div>

                          <div className="mt-4 sm:pl-7">
                            {!checked ? (
                              <button
                                disabled={!selected}
                                onClick={() =>
                                  setCheckedAnswers((p) => ({
                                    ...p,
                                    [i]: true,
                                  }))
                                }
                                className="btn-press rounded-md bg-white/[0.06] hover:bg-white/[0.1] px-4 py-2 text-xs font-medium text-[var(--text-primary)] border border-[var(--border)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                              >
                                Check answer
                              </button>
                            ) : (
                              <div
                                className={`mt-3 p-4 rounded-md text-xs leading-relaxed ${
                                  isCorrect
                                    ? "bg-[var(--success-dim)] border border-[var(--success)]/20"
                                    : "bg-[var(--error-dim)] border border-[var(--error)]/20"
                                }`}
                              >
                                <span className="font-medium block mb-1">
                                  {isCorrect
                                    ? "✓ Correct"
                                    : `✗ Correct answer: ${q.correct}`}
                                </span>
                                <p className="text-[var(--text-secondary)]">
                                  {q.explanation}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    <button
                      onClick={() => {
                        setSelectedAnswers({});
                        setCheckedAnswers({});
                      }}
                      className="btn-press text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] underline decoration-[var(--border)] underline-offset-4"
                    >
                      Reset all answers
                    </button>
                  </div>
                )}

                {/* Concept Timeline */}
                {result.study_assets?.concept_timeline?.length > 0 && (
                  <div className="mt-14 pt-8 border-t border-[var(--border)]">
                    <span className="font-mono text-xs uppercase tracking-[0.15em] text-[var(--text-tertiary)] block mb-6">
                      Concept timeline
                    </span>

                    <div className="space-y-4">
                      {result.study_assets.concept_timeline.map(
                        (item: any, i: number) => (
                          <div key={i} className="flex items-start gap-4">
                            <span className="font-mono text-xs text-[var(--accent)] min-w-[50px]">
                              {item.timestamp}s
                            </span>
                            <div>
                              <p className="text-sm font-medium text-[var(--text-primary)]">
                                {item.concept}
                              </p>
                              {item.importance && (
                                <p className="text-xs text-[var(--text-muted)] mt-0.5">
                                  Priority: {item.importance}
                                </p>
                              )}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}

                {/* Mind Map text */}
                {result.study_assets?.mind_map_text && (
                  <div className="mt-14 pt-8 border-t border-[var(--border)]">
                    <span className="font-mono text-xs uppercase tracking-[0.15em] text-[var(--text-tertiary)] block mb-4">
                      Hierarchical outline
                    </span>

                    <div className="rounded-lg border border-[var(--border)] bg-[#101114] p-5 font-mono text-xs leading-6 text-zinc-300 overflow-x-auto">
                      <pre>{result.study_assets.mind_map_text}</pre>
                    </div>
                  </div>
                )}
              </section>

              {/* ====== SECTION 6: ASK A QUESTION (Human & Grounded) ====== */}
              <section id="ask" className="py-12 scroll-mt-20">
                <span className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--text-muted)] block mb-2">
                  06 · Question & Answer
                </span>

                <h2 className="font-serif text-3xl font-normal text-[var(--text-primary)]">
                  Ask a question about this lesson
                </h2>

                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  Search across the full transcript, arguments, and
                  explanations.
                </p>

                <div className="mt-6 flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    placeholder="e.g. Why does backpropagation require the chain rule?"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAsk();
                    }}
                    className="h-11 min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[#121316] px-4 text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent-border)] transition-colors"
                  />

                  <button
                    onClick={handleAsk}
                    disabled={asking || !question.trim()}
                    className="btn-press shrink-0 rounded-lg bg-[var(--text-primary)] px-5 py-2.5 text-xs font-medium text-zinc-900 transition-colors hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {asking ? "Searching…" : "Ask question"}
                  </button>
                </div>

                {askError && (
                  <p className="mt-3 text-xs text-[var(--error)]">{askError}</p>
                )}

                <AnimatePresence>
                  {answer && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="mt-6 border-l-2 border-[var(--accent)] bg-[var(--accent-subtle)] p-5 rounded-r-lg"
                    >
                      <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--accent)] block mb-2">
                        Answer
                      </span>
                      <p className="text-sm leading-relaxed text-[var(--text-secondary)] whitespace-pre-line">
                        {answer}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </section>

              {/* ====== FOOTER ====== */}
              <footer className="pt-12 pb-16 border-t border-[var(--border)] flex items-center justify-between text-xs text-[var(--text-muted)]">
                <span>MindBook</span>
                <span>Your learning workspace</span>
              </footer>
            </article>
          </div>
        </div>
      )}
    </main>
  );
}
