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

type Tab =
  | "executive"
  | "deep-dive"
  | "knowledge"
  | "guide"
  | "study"
  | "ask";

// ============================================================
//  STAGES
// ============================================================
const STAGES = [
  { label: "Parsing the video", detail: "Fetching the transcript and metadata", icon: "📡" },
  { label: "Mapping the knowledge graph", detail: "Extracting concepts and how they connect", icon: "🧠" },
  { label: "Writing the deep dive", detail: "Building chunk-by-chunk explanations", icon: "📝" },
  { label: "Synthesizing the guide", detail: "Writing the summary and FAQ", icon: "✨" },
  { label: "Building study assets", detail: "Generating the quiz, timeline and mind map", icon: "🎯" },
];

const TABS: { id: Tab; label: string; description: string }[] = [
  { id: "executive", label: "Executive Summary", description: "The big picture" },
  { id: "deep-dive", label: "Deep Dive", description: "Detailed breakdowns" },
  { id: "knowledge", label: "Knowledge Graph", description: "Concepts & connections" },
  { id: "guide", label: "Complete Guide", description: "Full walkthrough" },
  { id: "study", label: "Study & Quiz", description: "Test your understanding" },
  { id: "ask", label: "Ask AI", description: "Ask anything" },
];

// ============================================================
//  SCROLL REVEAL HOOK
// ============================================================
function useReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, visible };
}

function RevealSection({
  children,
  className = "",
  stagger = false,
}: {
  children: React.ReactNode;
  className?: string;
  stagger?: boolean;
}) {
  const { ref, visible } = useReveal();
  return (
    <div
      ref={ref}
      className={`${stagger ? "reveal-stagger" : "reveal"} ${visible ? "visible" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

// ============================================================
//  RICH BLOCK RENDERER (editorial style, no square boxes)
// ============================================================
function RichBlock({ block }: { block: DeepDiveBlock }) {
  if (block.type === "heading")
    return (
      <h4 className="font-serif text-2xl tracking-tight text-[var(--text-primary)] md:text-3xl">
        {block.content}
      </h4>
    );

  if (block.type === "paragraph")
    return (
      <p className="prose-editorial">{block.content}</p>
    );

  if (block.type === "code")
    return (
      <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[#080808]">
        <div className="flex justify-between border-b border-[var(--border)] px-5 py-3 text-xs">
          <span className="text-[var(--accent)]">{block.caption || "Example"}</span>
          <span className="text-[var(--text-muted)]">{block.language || "text"}</span>
        </div>
        <pre className="overflow-x-auto p-5 text-sm leading-7 text-[var(--text-secondary)]">
          <code>{block.content}</code>
        </pre>
      </div>
    );

  if (block.type === "table") {
    const rows = String(block.content || "")
      .split("\n")
      .filter((row: string) => row.trim() && !/^\s*\|?\s*:?-+/.test(row));
    const cells = (row: string) =>
      row.split("|").map((cell) => cell.trim()).filter(Boolean);
    const [head, ...body] = rows.map(cells);
    return (
      <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead className="bg-white/[0.03] text-[var(--text-primary)]">
            <tr>
              {head?.map((cell: string, index: number) => (
                <th className="border-b border-[var(--border)] px-5 py-4 font-medium" key={index}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody className="text-[var(--text-secondary)]">
            {body.map((row: string[], rowIndex: number) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td className="border-b border-[var(--border)] px-5 py-4 last:border-0" key={cellIndex}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (block.type === "ascii_diagram")
    return (
      <pre className="overflow-x-auto rounded-xl border border-[var(--mint)]/15 bg-[var(--mint)]/[0.02] p-6 font-mono text-xs leading-7 text-[var(--mint)]">
        {block.content}
      </pre>
    );

  if (block.type === "callout")
    return (
      <div className="flex gap-4 rounded-xl bg-[var(--accent-dim)] px-6 py-5">
        <span className="mt-0.5 text-lg">💡</span>
        <div>
          <span className="text-xs font-semibold uppercase tracking-widest text-[var(--accent)]">
            {block.variant || "note"}
          </span>
          <p className="mt-1 text-sm leading-7 text-[var(--text-secondary)]">
            {block.content}
          </p>
        </div>
      </div>
    );

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

  const [selectedAnswers, setSelectedAnswers] = useState<{ [key: number]: string }>({});
  const [checkedAnswers, setCheckedAnswers] = useState<{ [key: number]: boolean }>({});

  // hero typing effect
  const [heroReady, setHeroReady] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setHeroReady(true), 200);
    return () => clearTimeout(t);
  }, []);

  // scroll-aware nav blur
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  // ============================================================
  //  API HANDLERS (unchanged logic)
  // ============================================================
  const handleGenerate = useCallback(async () => {
    if (!url.trim()) { setMessage("Please enter a YouTube URL."); return; }
    setMessage(""); setResult(null); setStageIndex(0); setPhase("processing");
    try {
      const response = await fetch("http://127.0.0.1:8000/process/stream", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
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
          const line = event.split("\n").find((item) => item.startsWith("data: "));
          if (!line) continue;
          const eventData = JSON.parse(line.slice(6));
          if (eventData.message) setMessage(eventData.message);
          if (typeof eventData.stage === "number") setStageIndex(eventData.stage);
          if (eventData.type === "error") throw new Error(eventData.message);
          if (eventData.type === "content") {
            setResult({
              video_id: "", content: { learning_objectives: [], topics: [], ...eventData.content },
              knowledge_graph: { nodes: [], edges: [] }, deep_dive: [],
              synthesis: { executive_summary: "", complete_guide: "", faq: [] },
              study_assets: { quiz: [], concept_timeline: [], mind_map_text: "" },
            });
          }
          if (eventData.type === "knowledge_graph")
            setResult((c: MindBookResult | null) => c ? { ...c, knowledge_graph: eventData.knowledge_graph } : c);
          if (eventData.type === "deep_dive_section")
            setResult((c: MindBookResult | null) => {
              if (!c) return c;
              const dd = [...(c?.deep_dive || [])];
              dd[eventData.section_index] = eventData.section;
              return { ...c, deep_dive: dd.filter(Boolean) };
            });
          if (eventData.type === "synthesis")
            setResult((c: MindBookResult | null) => c ? { ...c, synthesis: eventData.synthesis } : c);
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
      setResult(null); setMessage("Could not connect to FastAPI."); setPhase("failed");
    }
  }, [url]);

  const handleAsk = useCallback(async () => {
    if (!question.trim()) return;
    if (!videoId) { setAskError("Please generate a MindBook first."); return; }
    setAsking(true); setAnswer(""); setAskError("");
    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: videoId, question }),
      });
      if (!response.ok) throw new Error("Failed to get answer");
      const data = await response.json();
      setAnswer(data.answer);
    } catch (error) {
      console.error(error); setAskError("Could not get an answer.");
    } finally { setAsking(false); }
  }, [question, videoId]);

  const goToTab = (id: Tab) => {
    setActiveTab(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // ============================================================
  //  RENDER
  // ============================================================
  return (
    <main className="min-h-screen bg-[var(--bg)]">
      {/* ==============================================================
          NAV
      ============================================================== */}
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          scrolled
            ? "border-b border-[var(--border)] bg-black/80 backdrop-blur-2xl"
            : "bg-transparent"
        }`}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[var(--accent)] to-[var(--mint)] text-sm font-bold text-black">
              M
            </div>
            <span className="text-base font-medium tracking-tight text-[var(--text-primary)]">
              MindBook
            </span>
          </div>
          <div className="flex items-center gap-6">
            <span className="hidden items-center gap-2 text-xs text-[var(--text-muted)] md:flex">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--mint)]" />
              AI Study Environment
            </span>
          </div>
        </div>
      </motion.nav>

      {/* ==============================================================
          HERO / LANDING
      ============================================================== */}
      {phase !== "done" && !result && (
        <section className="relative flex min-h-screen items-center justify-center overflow-hidden">
          {/* Cinematic background */}
          <div className="hero-canvas">
            <div className="hero-orb hero-orb--1" />
            <div className="hero-orb hero-orb--2" />
            <div className="hero-orb hero-orb--3" />
            <div className="hero-grain" />
            <div className="hero-gradient-line" />
          </div>

          <div className="relative z-10 mx-auto max-w-4xl px-6 text-center">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={heroReady ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="mb-10 flex justify-center"
            >
              <span className="chip chip--accent">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" />
                AI-powered learning workspace
              </span>
            </motion.div>

            {/* Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={heroReady ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.9, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="font-serif text-5xl font-normal leading-[1.05] tracking-[-0.03em] text-[var(--text-primary)] sm:text-6xl md:text-7xl lg:text-[5.5rem]"
            >
              Understand any video.
              <br />
              <span className="bg-gradient-to-r from-[var(--accent)] to-[var(--mint)] bg-clip-text text-transparent">
                Deeply.
              </span>
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={heroReady ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="mx-auto mt-8 max-w-xl text-lg leading-relaxed text-[var(--text-tertiary)]"
            >
              Paste a lecture, tutorial, or talk. MindBook transforms it into clear explanations, connected concepts, and study material you'll actually remember.
            </motion.p>

            {/* Input or processing */}
            {phase === "idle" || phase === "failed" ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={heroReady ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="mx-auto mt-12 max-w-2xl"
              >
                <div className="flex overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--bg-elevated)] transition-all duration-300 focus-within:border-[var(--accent)]/40 focus-within:shadow-[0_0_40px_rgba(196,160,255,0.06)]">
                  <input
                    type="text"
                    placeholder="Paste a YouTube URL…"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") handleGenerate(); }}
                    className="h-14 min-w-0 flex-1 bg-transparent px-6 text-base text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
                  />
                  <button
                    onClick={handleGenerate}
                    className="btn-press m-1.5 rounded-xl bg-gradient-to-r from-[var(--accent)] to-[#a78bfa] px-8 text-sm font-semibold text-black transition-all hover:shadow-[0_4px_20px_rgba(196,160,255,0.25)]"
                  >
                    Generate
                  </button>
                </div>

                {message && (phase === "idle" || phase === "failed") && (
                  <p className="animate-fade-in mt-4 text-sm text-[var(--text-tertiary)]">{message}</p>
                )}
              </motion.div>
            ) : (
              /* Processing state */
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="mx-auto mt-12 max-w-lg"
              >
                <div className="content-card p-8">
                  <div className="flex items-center gap-3">
                    <span className="relative flex h-3 w-3">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--accent)]/50" />
                      <span className="relative inline-flex h-3 w-3 rounded-full bg-[var(--accent)]" />
                    </span>
                    <span className="text-xs font-medium uppercase tracking-widest text-[var(--accent)]">
                      Building your MindBook
                    </span>
                  </div>

                  {/* Progress */}
                  <div className="mt-6 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-[var(--accent)] to-[var(--mint)]"
                      initial={{ width: 0 }}
                      animate={{ width: `${((stageIndex + 1) / STAGES.length) * 100}%` }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                    />
                  </div>

                  <div className="mt-8 space-y-4">
                    {STAGES.map((stage, i) => {
                      const done = i < stageIndex;
                      const active = i === stageIndex;
                      return (
                        <div key={stage.label} className="flex items-start gap-3">
                          <div className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs transition-all ${
                            done ? "bg-[var(--mint-dim)] text-[var(--mint)]"
                              : active ? "bg-[var(--accent-dim)] text-[var(--accent)]"
                              : "bg-white/[0.04] text-[var(--text-muted)]"
                          }`}>
                            {done ? (
                              <svg className="animate-check-pop h-3 w-3" viewBox="0 0 20 20" fill="none">
                                <path d="M5 10l3 3 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            ) : active ? (
                              <span className="h-2 w-2 animate-pulse rounded-full bg-current" />
                            ) : (
                              <span>{stage.icon}</span>
                            )}
                          </div>
                          <div>
                            <p className={`text-sm ${done ? "text-[var(--text-secondary)]" : active ? "text-[var(--text-primary)]" : "text-[var(--text-muted)]"}`}>
                              {stage.label}
                            </p>
                            {active && <p className="animate-fade-in mt-0.5 text-xs text-[var(--text-tertiary)]">{stage.detail}</p>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Feature pills */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={heroReady ? { opacity: 1 } : {}}
              transition={{ duration: 1, delay: 0.6 }}
              className="mx-auto mt-20 flex flex-wrap items-center justify-center gap-3"
            >
              {["Executive summaries", "Knowledge graphs", "Deep dive explanations", "Interactive quizzes", "AI Q&A"].map((f) => (
                <span key={f} className="chip chip--ghost">{f}</span>
              ))}
            </motion.div>
          </div>
        </section>
      )}

      {/* ==============================================================
          RESULT WORKSPACE
      ============================================================== */}
      {(phase === "done" || phase === "processing") && result && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="mx-auto grid min-h-screen max-w-[1440px] grid-cols-1 pt-16 lg:grid-cols-[240px_minmax(0,1fr)]"
        >
          {/* ====== SIDEBAR ====== */}
          <aside className="hidden border-r border-[var(--border)] lg:block">
            <div className="sticky top-20 px-4 py-8">
              <div className="mb-8">
                <p className="mb-4 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                  Sections
                </p>
                <div className="space-y-1">
                  {TABS.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => goToTab(tab.id)}
                      className={`sidebar-link btn-press w-full text-left ${activeTab === tab.id ? "sidebar-link--active" : ""}`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-12 border-t border-[var(--border)] pt-6">
                <p className="px-3 text-[10px] uppercase tracking-[0.2em] text-[var(--text-muted)]">Status</p>
                <div className="mt-3 flex items-center gap-2 px-3 text-xs text-[var(--text-tertiary)]">
                  <span className={`h-1.5 w-1.5 rounded-full ${phase === "done" ? "bg-[var(--mint)]" : "animate-pulse bg-[var(--accent)]"}`} />
                  {phase === "done" ? "MindBook ready" : message || "Building…"}
                </div>
              </div>
            </div>
          </aside>

          {/* ====== MAIN CONTENT ====== */}
          <div className="min-w-0 px-6 py-8 md:px-10 lg:px-16 lg:py-12">

            {/* ====== HERO HEADER ====== */}
            <RevealSection className="pb-12">
              <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
                <span>MindBook</span>
                <span className="text-[var(--text-muted)]">/</span>
                <span>Generated Study Space</span>
              </div>
              <h1 className="mt-6 font-serif text-4xl font-normal leading-tight tracking-[-0.02em] text-[var(--text-primary)] md:text-5xl lg:text-6xl">
                {result.content.overall_topic}
              </h1>
              <div className="mt-6 flex flex-wrap gap-2">
                <span className="chip chip--accent">{result.content.content_type}</span>
                <span className="chip chip--ghost">{result.content.difficulty}</span>
                <span className="chip chip--ghost">{result.content.domain}</span>
              </div>
            </RevealSection>

            {/* ====== TAB NAV ====== */}
            <div className="sticky top-16 z-30 -mx-4 border-b border-[var(--border)] bg-black/90 px-4 backdrop-blur-xl">
              <div className="flex gap-1 overflow-x-auto py-2">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => goToTab(tab.id)}
                    className={`btn-press relative shrink-0 rounded-xl px-4 py-2.5 text-sm font-medium transition-all ${
                      activeTab === tab.id
                        ? "bg-white/[0.08] text-[var(--text-primary)]"
                        : "text-[var(--text-muted)] hover:bg-white/[0.04] hover:text-[var(--text-secondary)]"
                    }`}
                  >
                    {tab.label}
                    {activeTab === tab.id && (
                      <motion.span
                        layoutId="tab-indicator"
                        className="absolute inset-x-3 -bottom-2 h-0.5 rounded-full bg-[var(--accent)]"
                      />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* ==============================================================
                SECTION 1: EXECUTIVE SUMMARY
            ============================================================== */}
            <section id="executive" className="py-16">
              <RevealSection>
                <div className="mb-3 text-xs font-medium uppercase tracking-widest text-[var(--accent)]">
                  Executive Summary
                </div>
                <p className="max-w-3xl font-serif text-2xl leading-relaxed text-[var(--text-primary)] md:text-3xl md:leading-snug">
                  {result.synthesis.executive_summary}
                </p>
              </RevealSection>

              {/* Learning Objectives */}
              {result.content.learning_objectives?.length > 0 && (
                <RevealSection className="mt-16" stagger>
                  <p className="mb-6 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">
                    What you'll learn
                  </p>
                  {result.content.learning_objectives.map((obj: string, i: number) => (
                    <div key={i} className="flex gap-4 border-b border-[var(--border)] py-5 last:border-0">
                      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-dim)] text-xs font-medium text-[var(--accent)]">
                        {i + 1}
                      </span>
                      <p className="text-base leading-relaxed text-[var(--text-secondary)]">{obj}</p>
                    </div>
                  ))}
                </RevealSection>
              )}

              {/* Topics */}
              {result.content.topics?.length > 0 && (
                <RevealSection className="mt-16">
                  <p className="mb-6 text-xs font-medium uppercase tracking-widest text-[var(--accent)]">
                    Topics Covered
                  </p>
                  <div className="space-y-6">
                    {result.content.topics.map((topic: any, i: number) => (
                      <div key={i} className="group">
                        <h3 className="text-lg font-medium text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
                          {topic.title}
                        </h3>
                        <p className="mt-2 max-w-3xl text-sm leading-7 text-[var(--text-tertiary)]">
                          {topic.summary}
                        </p>
                      </div>
                    ))}
                  </div>
                </RevealSection>
              )}

              {/* FAQ */}
              {result.synthesis.faq?.length > 0 && (
                <RevealSection className="mt-16">
                  <p className="mb-6 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">
                    Frequently Asked
                  </p>
                  <div className="space-y-8">
                    {result.synthesis.faq.map((item: any, i: number) => (
                      <div key={i}>
                        <h4 className="font-serif text-xl text-[var(--text-primary)]">{item.q}</h4>
                        <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--text-tertiary)]">{item.a}</p>
                      </div>
                    ))}
                  </div>
                </RevealSection>
              )}
            </section>

            <div className="section-divider" />

            {/* ==============================================================
                SECTION 2: DEEP DIVE
            ============================================================== */}
            <section id="deep-dive" className="py-16">
              <RevealSection>
                <div className="mb-2 text-xs font-medium uppercase tracking-widest text-[var(--accent)]">
                  Deep Dive
                </div>
                <h2 className="font-serif text-3xl text-[var(--text-primary)] md:text-4xl">
                  Detailed Breakdown
                </h2>
                <p className="mt-3 max-w-2xl text-base text-[var(--text-tertiary)]">
                  Each concept explained in depth, organized as a learning journey.
                </p>
              </RevealSection>

              <div className="mt-12 space-y-20">
                {result.deep_dive.map((chunk: any, i: number) => (
                  <RevealSection key={chunk.chunk_id ?? i}>
                    <article>
                      <div className="flex items-center gap-4">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-dim)] font-mono text-xs font-medium text-[var(--accent)]">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <div className="h-px flex-1 bg-[var(--border)]" />
                        <span className="chip chip--accent">
                          Difficulty {chunk.result.difficulty_rating}/5
                        </span>
                      </div>

                      <h3 className="mt-6 font-serif text-2xl text-[var(--text-primary)] md:text-3xl">
                        Chunk {chunk.chunk_id}
                      </h3>

                      <div className="mt-8 max-w-3xl space-y-8">
                        {chunk.result.blocks.map((block: any, bi: number) => (
                          <RichBlock key={bi} block={block} />
                        ))}
                      </div>

                      {/* Key concepts */}
                      {chunk.result.key_concepts?.length > 0 && (
                        <div className="mt-10">
                          <p className="mb-3 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">Key Concepts</p>
                          <div className="flex flex-wrap gap-2">
                            {chunk.result.key_concepts.map((c: string, ci: number) => (
                              <span key={ci} className="graph-node">{c}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Sketch note */}
                      {chunk.result.sketch_note && (
                        <div className="mt-10 content-card p-6">
                          <p className="text-xs font-medium uppercase tracking-widest text-[var(--accent)]">Visual Note</p>
                          <h4 className="mt-2 font-serif text-xl text-[var(--text-primary)]">{chunk.result.sketch_note.title}</h4>
                          <p className="mt-1 text-xs text-[var(--text-muted)]">{chunk.result.sketch_note.subtitle}</p>
                          <ul className="mt-5 space-y-3">
                            {chunk.result.sketch_note.boxes?.map((box: string, bi: number) => (
                              <li key={bi} className="flex gap-3 text-sm leading-relaxed text-[var(--text-secondary)]">
                                <span className="text-[var(--mint)]">—</span>
                                <span>{box}</span>
                              </li>
                            ))}
                          </ul>
                          {chunk.result.sketch_note.takeaway && (
                            <div className="mt-6 border-t border-[var(--border)] pt-5">
                              <p className="text-xs font-medium uppercase tracking-widest text-[var(--text-muted)]">Takeaway</p>
                              <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{chunk.result.sketch_note.takeaway}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </article>
                  </RevealSection>
                ))}
              </div>
            </section>

            <div className="section-divider" />

            {/* ==============================================================
                SECTION 3: KNOWLEDGE GRAPH
            ============================================================== */}
            <section id="knowledge" className="py-16">
              <RevealSection>
                <div className="mb-2 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">
                  Knowledge Graph
                </div>
                <h2 className="font-serif text-3xl text-[var(--text-primary)] md:text-4xl">
                  Concepts & Connections
                </h2>
                <p className="mt-3 max-w-2xl text-base text-[var(--text-tertiary)]">
                  How the ideas in this material relate to each other.
                </p>
              </RevealSection>

              <RevealSection className="mt-10">
                <p className="mb-4 text-xs font-medium uppercase tracking-widest text-[var(--text-muted)]">Concepts</p>
                <div className="flex flex-wrap gap-2">
                  {result.knowledge_graph.nodes.map((node: any, i: number) => (
                    <span key={i} className="graph-node">{node.label || node.name || node.id}</span>
                  ))}
                </div>
              </RevealSection>

              <RevealSection className="mt-12">
                <p className="mb-4 text-xs font-medium uppercase tracking-widest text-[var(--text-muted)]">Relationships</p>
                <div className="space-y-2">
                  {result.knowledge_graph.edges.map((edge: any, i: number) => {
                    const from = result.knowledge_graph.nodes.find((n: any) => n.id === edge.from);
                    const to = result.knowledge_graph.nodes.find((n: any) => n.id === edge.to);
                    return (
                      <div key={i} className="graph-edge">
                        <span className="text-sm font-medium text-[var(--text-primary)]">{from?.label || edge.from}</span>
                        <span className="text-[var(--accent)]">→</span>
                        <span className="text-sm text-[var(--text-tertiary)]">{edge.relation}</span>
                        <span className="text-[var(--mint)]">→</span>
                        <span className="text-sm font-medium text-[var(--text-primary)]">{to?.label || edge.to}</span>
                      </div>
                    );
                  })}
                </div>
              </RevealSection>
            </section>

            <div className="section-divider" />

            {/* ==============================================================
                SECTION 4: COMPLETE GUIDE
            ============================================================== */}
            <section id="guide" className="py-16">
              <RevealSection>
                <div className="mb-2 text-xs font-medium uppercase tracking-widest text-[var(--accent)]">
                  Complete Guide
                </div>
                <h2 className="font-serif text-3xl text-[var(--text-primary)] md:text-4xl">
                  Full Walkthrough
                </h2>
              </RevealSection>

              <RevealSection className="mt-8">
                <div className="max-w-3xl whitespace-pre-line text-base leading-8 text-[var(--text-secondary)]">
                  {result.synthesis.complete_guide}
                </div>
              </RevealSection>
            </section>

            <div className="section-divider" />

            {/* ==============================================================
                SECTION 5: STUDY & QUIZ
            ============================================================== */}
            <section id="study" className="py-16">
              <RevealSection>
                <div className="mb-2 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">
                  Study & Quiz
                </div>
                <h2 className="font-serif text-3xl text-[var(--text-primary)] md:text-4xl">
                  Test Your Understanding
                </h2>
                <p className="mt-3 max-w-2xl text-base text-[var(--text-tertiary)]">
                  Interactive quiz, concept timeline, and mind map to help you retain what you've learned.
                </p>
              </RevealSection>

              {/* Quiz */}
              {result.study_assets.quiz?.length > 0 && (
                <RevealSection className="mt-12">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-medium uppercase tracking-widest text-[var(--accent)]">Knowledge Check</p>
                    <span className="text-xs text-[var(--text-muted)]">{result.study_assets.quiz.length} questions</span>
                  </div>

                  <div className="mt-6 space-y-12">
                    {result.study_assets.quiz.map((q: any, i: number) => {
                      const selected = selectedAnswers[i];
                      const checked = checkedAnswers[i];
                      const isCorrect = selected === q.correct;

                      return (
                        <div key={i} className="content-card p-6">
                          <div className="flex items-start gap-4">
                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--accent-dim)] text-xs font-medium text-[var(--accent)]">
                              {i + 1}
                            </span>
                            <h4 className="text-base font-medium leading-relaxed text-[var(--text-primary)]">{q.question}</h4>
                          </div>

                          <div className="mt-5 space-y-2 pl-11">
                            {q.options.map((opt: string, oi: number) => {
                              const letter = opt.split(")")[0];
                              const isSelected = selected === letter;
                              const showCorrect = checked && letter === q.correct;
                              const showWrong = checked && isSelected && !isCorrect;

                              return (
                                <button
                                  key={oi}
                                  onClick={() => setSelectedAnswers((p) => ({ ...p, [i]: letter }))}
                                  className={`quiz-option ${isSelected && !checked ? "quiz-option--selected" : ""} ${showCorrect ? "quiz-option--correct" : ""} ${showWrong ? "quiz-option--wrong" : ""}`}
                                  disabled={!!checked}
                                >
                                  {opt}
                                </button>
                              );
                            })}
                          </div>

                          <div className="mt-4 pl-11">
                            {!checked && (
                              <button
                                disabled={!selected}
                                onClick={() => setCheckedAnswers((p) => ({ ...p, [i]: true }))}
                                className="btn-press rounded-xl bg-[var(--accent-dim)] px-5 py-2.5 text-sm font-medium text-[var(--accent)] transition-all hover:bg-[var(--accent)]/20 disabled:cursor-not-allowed disabled:opacity-30"
                              >
                                Check Answer
                              </button>
                            )}

                            <AnimatePresence>
                              {checked && (
                                <motion.div
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: "auto" }}
                                  exit={{ opacity: 0, height: 0 }}
                                  className={`mt-4 overflow-hidden rounded-xl p-5 ${
                                    isCorrect ? "bg-[var(--mint-dim)]" : "bg-red-500/[0.06]"
                                  }`}
                                >
                                  <p className={`text-sm font-medium ${isCorrect ? "text-[var(--mint)]" : "text-red-300"}`}>
                                    {isCorrect ? "✓ Correct!" : "✗ Not quite"}
                                  </p>
                                  {!isCorrect && (
                                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                                      Correct answer: <strong className="text-[var(--text-secondary)]">{q.correct}</strong>
                                    </p>
                                  )}
                                  <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{q.explanation}</p>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => { setSelectedAnswers({}); setCheckedAnswers({}); }}
                    className="btn-press mt-6 rounded-xl border border-[var(--border)] px-5 py-2.5 text-sm text-[var(--text-tertiary)] hover:border-[var(--border-hover)] hover:text-[var(--text-primary)]"
                  >
                    Reset Quiz
                  </button>
                </RevealSection>
              )}

              {/* Timeline */}
              {result.study_assets.concept_timeline?.length > 0 && (
                <RevealSection className="mt-20">
                  <p className="mb-6 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">Concept Timeline</p>
                  <div className="space-y-0">
                    {result.study_assets.concept_timeline.map((item: any, i: number) => (
                      <div key={i} className="flex items-center gap-5 border-b border-[var(--border)] py-5 last:border-0">
                        <span className="min-w-[60px] font-mono text-xs text-[var(--accent)]">{item.timestamp}s</span>
                        <div className="h-px w-4 bg-[var(--border)]" />
                        <div>
                          <p className="font-serif text-lg text-[var(--text-primary)]">{item.concept}</p>
                          <p className="mt-0.5 text-xs text-[var(--text-muted)]">Importance: {item.importance}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </RevealSection>
              )}

              {/* Mind Map */}
              {result.study_assets.mind_map_text && (
                <RevealSection className="mt-20">
                  <p className="mb-6 text-xs font-medium uppercase tracking-widest text-[var(--accent)]">Mind Map</p>
                  <div className="content-card p-6">
                    <div className="space-y-1.5">
                      {result.study_assets.mind_map_text.split("\n").map((line: string, i: number) => {
                        const trimmed = line.trim();
                        if (!trimmed) return null;
                        const spaces = line.length - line.trimStart().length;
                        const level = Math.floor(spaces / 2);
                        return (
                          <div
                            key={i}
                            style={{ marginLeft: `${level * 24}px` }}
                            className={`rounded-lg px-4 py-2.5 transition-colors hover:bg-white/[0.03] ${
                              level === 0
                                ? "font-serif text-lg text-[var(--text-primary)]"
                                : level === 1
                                  ? "text-sm text-[var(--text-secondary)]"
                                  : "text-xs text-[var(--text-tertiary)]"
                            }`}
                          >
                            {level > 0 && (
                              <span className="mr-2 text-[var(--mint)]">
                                {level === 1 ? "└" : "•"}
                              </span>
                            )}
                            {trimmed}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </RevealSection>
              )}
            </section>

            <div className="section-divider" />

            {/* ==============================================================
                SECTION 6: ASK AI
            ============================================================== */}
            <section id="ask" className="py-16">
              <RevealSection>
                <div className="content-card overflow-hidden">
                  <div className="border-b border-[var(--border)] p-8">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--mint)]" />
                      Ask AI
                    </div>
                    <h2 className="mt-3 font-serif text-3xl text-[var(--text-primary)] md:text-4xl">
                      Ask about this video.
                    </h2>
                    <p className="mt-3 max-w-xl text-sm leading-relaxed text-[var(--text-tertiary)]">
                      Ask questions about the concepts explained in this video. MindBook retrieves relevant sections before generating the answer.
                    </p>
                  </div>

                  <div className="p-8">
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <input
                        type="text"
                        placeholder="What do you want to know?"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") handleAsk(); }}
                        className="h-12 min-w-0 flex-1 rounded-xl border border-[var(--border)] bg-transparent px-5 text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] transition-colors focus:border-[var(--mint)]/40"
                      />
                      <button
                        onClick={handleAsk}
                        disabled={asking || !question.trim()}
                        className="btn-press h-12 rounded-xl bg-[var(--mint)] px-7 text-sm font-semibold text-black transition-all hover:shadow-[0_4px_20px_rgba(110,231,183,0.2)] disabled:cursor-not-allowed disabled:bg-[var(--bg-surface)] disabled:text-[var(--text-muted)]"
                      >
                        {asking ? (
                          <span className="flex items-center gap-2">
                            <span className="h-3 w-3 animate-spin rounded-full border-2 border-black/20 border-t-black" />
                            Thinking…
                          </span>
                        ) : "Ask"}
                      </button>
                    </div>

                    {askError && <p className="animate-fade-in mt-4 text-xs text-red-300">{askError}</p>}

                    <AnimatePresence>
                      {answer && (
                        <motion.div
                          initial={{ opacity: 0, y: 16 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -8 }}
                          className="mt-8"
                        >
                          <p className="mb-3 text-xs font-medium uppercase tracking-widest text-[var(--mint)]">Answer</p>
                          <p className="whitespace-pre-line text-base leading-8 text-[var(--text-secondary)]">{answer}</p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </RevealSection>
            </section>

            {/* ====== FOOTER ====== */}
            <footer className="border-t border-[var(--border)] py-10">
              <div className="flex flex-col justify-between gap-3 text-xs text-[var(--text-muted)] sm:flex-row">
                <span>MindBook</span>
                <span>Understand · Connect · Remember</span>
              </div>
            </footer>
          </div>
        </motion.div>
      )}
    </main>
  );
}
