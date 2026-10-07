"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ============================================================
// TYPES
// ============================================================

type DeepDiveBlock = {
  type: string;
  content: string;
  caption?: string;
  language?: string;
  variant?: string;
};

type DeepDiveChapter = {
  chunk_id?: string;
  result?: {
    blocks?: DeepDiveBlock[];
    key_concepts?: string[];
    difficulty_rating?: string;
  };
};

type MindBookResult = {
  video_id?: string;

  content?: {
    overall_topic?: string;
    thumbnail?: string;
    content_type?: string;
    difficulty?: string;
    domain?: string;
  };

  synthesis?: {
    executive_summary?: string;
  };

  deep_dive?: DeepDiveChapter[];
};

// ============================================================
// PROGRESS STAGES
// ============================================================

const PROGRESS_STAGES = [
  "Fetching transcript",
  "Parsing content",
  "Creating deep dive summaries",
  "Finalizing results",
];

// ============================================================
// MAIN COMPONENT
// ============================================================

export default function Home() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<MindBookResult | null>(null);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");

  // ----------------------------------------------------------
  // GENERATE MINDBOOK
  // ----------------------------------------------------------

  const handleGenerate = async () => {
    if (!url.trim()) {
      setMessage("Please enter a YouTube URL.");
      return;
    }

    setLoading(true);
    setResult(null);
    setMessage("Starting...");

    try {
      const response = await fetch(`${API_URL}/process/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to process video.");
      }

      if (!response.body) {
        throw new Error("Streaming is not supported.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, {
          stream: true,
        });

        const events = buffer.split("\n\n");

        buffer = events.pop() || "";

        for (const event of events) {
          const lines = event.split("\n");

          for (const line of lines) {
            if (!line.startsWith("data:")) {
              continue;
            }

            const rawData = line.slice(5).trim();

            if (!rawData) {
              continue;
            }

            try {
              const data = JSON.parse(rawData);

              // Backend progress message
              if (data.message) {
                setMessage(data.message);
              }

              // Final result
              if (data.type === "complete") {
                setResult(data.result);
                setMessage("Complete!");
              }

              if (data.type === "error") {
                throw new Error(data.message || "Something went wrong.");
              }
            } catch (error) {
              console.error("SSE parsing error:", error);
            }
          }
        }
      }
    } catch (error) {
      console.error(error);

      setMessage(
        error instanceof Error ? error.message : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  };

  // ----------------------------------------------------------
  // ASK RAG
  // ----------------------------------------------------------

  const handleAsk = async () => {
    if (!question.trim() || !result?.video_id) {
      return;
    }

    setAsking(true);
    setAskError("");
    setAnswer("");

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          video_id: result.video_id,
          question: question.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to get answer.");
      }

      setAnswer(data.answer || "");
    } catch (error) {
      setAskError(
        error instanceof Error ? error.message : "Something went wrong."
      );
    } finally {
      setAsking(false);
    }
  };

  // ----------------------------------------------------------
  // RESET
  // ----------------------------------------------------------

  const handleReset = () => {
    setUrl("");
    setResult(null);
    setMessage("");
    setQuestion("");
    setAnswer("");
    setAskError("");
  };

  // ----------------------------------------------------------
  // GET CURRENT PROGRESS
  // ----------------------------------------------------------

  const getProgressIndex = () => {
    const text = message.toLowerCase();

    if (text.includes("transcript") || text.includes("fetch")) {
      return 0;
    }

    if (text.includes("parse") || text.includes("content")) {
      return 1;
    }

    if (
      text.includes("deep") ||
      text.includes("summary") ||
      text.includes("chunk")
    ) {
      return 2;
    }

    if (
      text.includes("synth") ||
      text.includes("final") ||
      text.includes("complete")
    ) {
      return 3;
    }

    return 0;
  };

  const progressIndex = getProgressIndex();

  // ============================================================
  // UI
  // ============================================================

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      {/* ======================================================
          HEADER
      ====================================================== */}

      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-bold">MindBook</h1>

          {result && (
            <button
              onClick={handleReset}
              className="rounded-lg border px-4 py-2 text-sm hover:bg-gray-100"
            >
              New Video
            </button>
          )}
        </div>
      </header>

      {/* ======================================================
          INPUT PAGE
      ====================================================== */}

      {!result && !loading && (
        <section className="mx-auto max-w-3xl px-6 py-20">
          <div className="text-center">
            <h2 className="text-4xl font-bold">
              Turn YouTube videos into MindBooks
            </h2>

            <p className="mt-4 text-gray-600">
              Generate a concise overview, deep dive summaries, and ask
              questions using RAG.
            </p>
          </div>

          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste YouTube URL..."
              className="flex-1 rounded-xl border bg-white px-4 py-3 outline-none focus:border-black"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleGenerate();
                }
              }}
            />

            <button
              onClick={handleGenerate}
              className="rounded-xl bg-black px-6 py-3 font-medium text-white hover:bg-gray-800"
            >
              Generate
            </button>
          </div>
        </section>
      )}

      {/* ======================================================
          PROGRESS
      ====================================================== */}

      {loading && (
        <section className="mx-auto max-w-2xl px-6 py-20">
          <div className="rounded-2xl border bg-white p-8 shadow-sm">
            <div className="text-center">
              <div className="mx-auto mb-5 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

              <h2 className="text-2xl font-bold">Generating your MindBook</h2>

              <p className="mt-2 text-sm text-gray-500">
                {message || "Processing your video..."}
              </p>
            </div>

            {/* Progress stages */}

            <div className="mt-8 space-y-4">
              {PROGRESS_STAGES.map((stage, index) => {
                const completed = index < progressIndex;

                const current = index === progressIndex;

                return (
                  <div key={stage} className="flex items-center gap-3">
                    {/* Status icon */}

                    <div
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-medium ${
                        completed
                          ? "bg-black text-white"
                          : current
                          ? "border-2 border-black"
                          : "border border-gray-300 text-gray-400"
                      }`}
                    >
                      {completed ? "✓" : index + 1}
                    </div>

                    {/* Stage name */}

                    <span
                      className={
                        completed
                          ? "text-sm text-gray-900"
                          : current
                          ? "text-sm font-medium text-gray-900"
                          : "text-sm text-gray-400"
                      }
                    >
                      {stage}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {/* ======================================================
          RESULT
      ====================================================== */}

      {result && (
        <section className="mx-auto max-w-4xl px-6 py-10">
          {/* --------------------------------------------------
              TITLE
          -------------------------------------------------- */}

          <h2 className="text-3xl font-bold">
            {result.content?.overall_topic || "MindBook"}
          </h2>

          {/* --------------------------------------------------
              THUMBNAIL
          -------------------------------------------------- */}

          {result.content?.thumbnail && (
            <img
              src={result.content.thumbnail}
              alt={result.content.overall_topic || "Video thumbnail"}
              className="mt-6 w-full rounded-2xl object-cover"
            />
          )}

          {/* --------------------------------------------------
              OVERVIEW
          -------------------------------------------------- */}

          <section className="mt-8 rounded-2xl border bg-white p-6">
            <h3 className="text-xl font-semibold">Overview</h3>

            <p className="mt-4 whitespace-pre-line leading-7 text-gray-700">
              {result.synthesis?.executive_summary || "No overview available."}
            </p>
          </section>

          {/* --------------------------------------------------
              DEEP DIVE
          -------------------------------------------------- */}

          <section className="mt-10">
            <h3 className="text-2xl font-bold">Deep Dive</h3>

            <p className="mt-2 text-gray-600">
              Chapter-by-chapter explanations.
            </p>

            <div className="mt-6 space-y-6">
              {result.deep_dive?.map((chapter, index) => (
                <article
                  key={chapter.chunk_id || index}
                  className="rounded-2xl border bg-white p-6"
                >
                  <h4 className="text-lg font-semibold">Chapter {index + 1}</h4>

                  {/* Blocks */}

                  <div className="mt-5 space-y-4">
                    {chapter.result?.blocks?.map((block, blockIndex) => (
                      <DeepDiveBlock key={blockIndex} block={block} />
                    ))}
                  </div>

                  {/* Key concepts */}

                  {chapter.result?.key_concepts &&
                    chapter.result.key_concepts.length > 0 && (
                      <div className="mt-6">
                        <h5 className="font-semibold">Key Concepts</h5>

                        <div className="mt-3 flex flex-wrap gap-2">
                          {chapter.result.key_concepts.map(
                            (concept, conceptIndex) => (
                              <span
                                key={conceptIndex}
                                className="rounded-full bg-gray-100 px-3 py-1 text-sm"
                              >
                                {concept}
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    )}
                </article>
              ))}
            </div>
          </section>

          {/* ==================================================
              RAG
          ================================================== */}

          <section className="mt-12 rounded-2xl border bg-white p-6">
            <h3 className="text-2xl font-bold">Ask MindBook</h3>

            <p className="mt-2 text-gray-600">
              Ask questions about this video.
            </p>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask something..."
                className="flex-1 rounded-xl border px-4 py-3 outline-none focus:border-black"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleAsk();
                  }
                }}
              />

              <button
                onClick={handleAsk}
                disabled={asking}
                className="rounded-xl bg-black px-6 py-3 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {asking ? "Thinking..." : "Ask"}
              </button>
            </div>

            {/* RAG error */}

            {askError && (
              <p className="mt-4 text-sm text-red-600">{askError}</p>
            )}

            {/* RAG answer */}

            {answer && (
              <div className="mt-6 rounded-xl bg-gray-50 p-5">
                <h4 className="font-semibold">Answer</h4>

                <p className="mt-3 whitespace-pre-line leading-7 text-gray-700">
                  {answer}
                </p>
              </div>
            )}
          </section>
        </section>
      )}

      {/* ======================================================
          FOOTER
      ====================================================== */}

      <footer className="py-10 text-center text-sm text-gray-400">
        MindBook
      </footer>
    </main>
  );
}

// ============================================================
// DEEP DIVE BLOCK
// ============================================================

function DeepDiveBlock({ block }: { block: DeepDiveBlock }) {
  if (!block.content) {
    return null;
  }

  // Heading

  if (block.type === "heading") {
    return <h5 className="text-lg font-semibold">{block.content}</h5>;
  }

  // Code

  if (block.type === "code") {
    return (
      <pre className="overflow-x-auto rounded-xl bg-gray-900 p-4 text-sm text-white">
        <code>{block.content}</code>
      </pre>
    );
  }

  // ASCII diagram

  if (block.type === "ascii_diagram") {
    return (
      <pre className="overflow-x-auto rounded-xl bg-gray-50 p-4 text-sm">
        {block.content}
      </pre>
    );
  }

  // Callout

  if (block.type === "callout") {
    return (
      <div className="rounded-xl border-l-4 border-gray-400 bg-gray-50 p-4">
        <p className="text-gray-700">{block.content}</p>
      </div>
    );
  }

  // Table

  if (block.type === "table") {
    return (
      <div className="overflow-x-auto rounded-xl border">
        <pre className="p-4 text-sm">{block.content}</pre>
      </div>
    );
  }

  // Default paragraph

  return (
    <p className="whitespace-pre-line leading-7 text-gray-700">
      {block.content}
    </p>
  );
}
