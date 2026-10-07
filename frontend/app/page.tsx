"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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
    difficulty_rating?: number;
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

export default function Home() {
  // -----------------------------
  // Basic frontend state
  // -----------------------------

  const [url, setUrl] = useState("");
  const [result, setResult] = useState<MindBookResult | null>(null);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // RAG state
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");

  // -----------------------------
  // Generate MindBook
  // -----------------------------

  async function handleGenerate() {
    if (!url.trim()) {
      setMessage("Please enter a YouTube URL.");
      return;
    }

    setLoading(true);
    setMessage("Processing video...");
    setResult(null);
    setAnswer("");
    setAskError("");

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
        throw new Error("Streaming is not available.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, {
          stream: true,
        });

        const events = buffer.split("\n\n");

        buffer = events.pop() || "";

        for (const event of events) {
          const line = event
            .split("\n")
            .find((line) => line.startsWith("data: "));

          if (!line) continue;

          const data = JSON.parse(line.slice(6));

          // Show backend progress message
          if (data.message) {
            setMessage(data.message);
          }

          // Backend finished everything
          if (data.type === "complete") {
            setResult(data.result);
            setMessage("Done!");
          }

          if (data.type === "error") {
            throw new Error(data.message || "Processing failed.");
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
  }

  // -----------------------------
  // Ask RAG question
  // -----------------------------

  async function handleAsk() {
    if (!question.trim()) return;

    if (!result?.video_id) {
      setAskError("Please generate a MindBook first.");
      return;
    }

    setAsking(true);
    setAnswer("");
    setAskError("");

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

      if (!response.ok) {
        throw new Error("Failed to get answer.");
      }

      const data = await response.json();

      setAnswer(data.answer);
    } catch (error) {
      console.error(error);

      setAskError(
        error instanceof Error ? error.message : "Could not get an answer."
      );
    } finally {
      setAsking(false);
    }
  }

  // -----------------------------
  // Reset
  // -----------------------------

  function handleReset() {
    setUrl("");
    setResult(null);
    setMessage("");
    setQuestion("");
    setAnswer("");
    setAskError("");
  }

  // -----------------------------
  // UI
  // -----------------------------

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* --------------------------------
          Header
      -------------------------------- */}

      <header className="border-b border-zinc-800">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
          <h1 className="text-xl font-semibold">MindBook</h1>

          {result && (
            <button
              onClick={handleReset}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
            >
              New Video
            </button>
          )}
        </div>
      </header>

      {/* --------------------------------
          Input
      -------------------------------- */}

      {!result && (
        <section className="mx-auto max-w-3xl px-5 py-24">
          <div className="text-center">
            <h2 className="text-4xl font-bold">
              Turn a YouTube video into a MindBook
            </h2>

            <p className="mt-4 text-zinc-400">
              Get a concise overview, chapter-by-chapter deep dive, and ask
              questions using RAG.
            </p>
          </div>

          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleGenerate();
                }
              }}
              placeholder="Paste YouTube URL..."
              className="h-12 flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 outline-none placeholder:text-zinc-500 focus:border-zinc-500"
            />

            <button
              onClick={handleGenerate}
              disabled={loading}
              className="h-12 rounded-lg bg-white px-6 font-medium text-black hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Processing..." : "Generate"}
            </button>
          </div>

          {message && (
            <p className="mt-4 text-center text-sm text-zinc-400">{message}</p>
          )}
        </section>
      )}

      {/* --------------------------------
          Result
      -------------------------------- */}

      {result && (
        <div className="mx-auto max-w-4xl px-5 py-10">
          {/* --------------------------------
              Title + Thumbnail
          -------------------------------- */}

          <section>
            <h2 className="text-3xl font-bold sm:text-4xl">
              {result.content?.overall_topic || "Untitled Video"}
            </h2>

            {result.content?.thumbnail && (
              <img
                src={result.content.thumbnail}
                alt={result.content.overall_topic || "Video"}
                className="mt-6 w-full rounded-xl object-cover"
              />
            )}
          </section>

          {/* --------------------------------
              Overview
          -------------------------------- */}

          <section className="mt-12 border-t border-zinc-800 pt-10">
            <h3 className="text-2xl font-semibold">Overview</h3>

            <p className="mt-4 whitespace-pre-line text-base leading-8 text-zinc-300">
              {result.synthesis?.executive_summary || "No overview available."}
            </p>
          </section>

          {/* --------------------------------
              Deep Dive
          -------------------------------- */}

          <section className="mt-12 border-t border-zinc-800 pt-10">
            <h3 className="text-2xl font-semibold">Deep Dive</h3>

            <p className="mt-2 text-sm text-zinc-500">
              Chapter-by-chapter explanation.
            </p>

            <div className="mt-10 space-y-12">
              {result.deep_dive?.map((chapter, index) => (
                <article
                  key={chapter.chunk_id || index}
                  className="border-t border-zinc-800 pt-8 first:border-t-0 first:pt-0"
                >
                  {/* Chapter title */}

                  <h4 className="text-xl font-semibold">Chapter {index + 1}</h4>

                  {/* Difficulty */}

                  {chapter.result?.difficulty_rating && (
                    <p className="mt-1 text-xs text-zinc-500">
                      Difficulty: {chapter.result.difficulty_rating}/5
                    </p>
                  )}

                  {/* Blocks */}

                  <div className="mt-6 space-y-6">
                    {chapter.result?.blocks?.map((block, blockIndex) => (
                      <DeepDiveBlock key={blockIndex} block={block} />
                    ))}
                  </div>

                  {/* Key concepts */}

                  {chapter.result?.key_concepts &&
                    chapter.result.key_concepts.length > 0 && (
                      <div className="mt-8">
                        <h5 className="text-sm font-medium text-zinc-400">
                          Key concepts
                        </h5>

                        <div className="mt-3 flex flex-wrap gap-2">
                          {chapter.result.key_concepts.map((concept, i) => (
                            <span
                              key={i}
                              className="rounded-full bg-zinc-800 px-3 py-1 text-xs text-zinc-300"
                            >
                              {concept}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                </article>
              ))}
            </div>
          </section>

          {/* --------------------------------
              RAG
          -------------------------------- */}

          <section className="mt-16 border-t border-zinc-800 pt-10">
            <h3 className="text-2xl font-semibold">Ask MindBook</h3>

            <p className="mt-2 text-sm text-zinc-500">
              Ask questions about this video.
            </p>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleAsk();
                  }
                }}
                placeholder="Ask something about this video..."
                className="h-12 flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 outline-none placeholder:text-zinc-500 focus:border-zinc-500"
              />

              <button
                onClick={handleAsk}
                disabled={asking || !question.trim()}
                className="h-12 rounded-lg bg-white px-6 font-medium text-black hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {asking ? "Thinking..." : "Ask"}
              </button>
            </div>

            {askError && (
              <p className="mt-4 text-sm text-red-400">{askError}</p>
            )}

            {answer && (
              <div className="mt-6 rounded-lg border border-zinc-800 bg-zinc-900 p-6">
                <h4 className="text-sm font-medium text-zinc-400">Answer</h4>

                <p className="mt-3 whitespace-pre-line leading-7 text-zinc-200">
                  {answer}
                </p>
              </div>
            )}
          </section>

          {/* --------------------------------
              Footer
          -------------------------------- */}

          <footer className="mt-16 border-t border-zinc-800 py-8 text-center text-sm text-zinc-600">
            MindBook
          </footer>
        </div>
      )}
    </main>
  );
}

/* ============================================================
   Deep Dive Block
   ============================================================ */

function DeepDiveBlock({ block }: { block: DeepDiveBlock }) {
  // Heading
  if (block.type === "heading") {
    return <h5 className="text-xl font-semibold">{block.content}</h5>;
  }

  // Paragraph
  if (block.type === "paragraph") {
    return (
      <p className="whitespace-pre-line leading-8 text-zinc-300">
        {block.content}
      </p>
    );
  }

  // Code
  if (block.type === "code") {
    return (
      <div className="overflow-hidden rounded-lg border border-zinc-800 bg-black">
        <div className="border-b border-zinc-800 px-4 py-2 text-xs text-zinc-500">
          {block.caption || block.language || "Code"}
        </div>

        <pre className="overflow-x-auto p-4 text-sm leading-6 text-zinc-300">
          <code>{block.content}</code>
        </pre>
      </div>
    );
  }

  // Callout
  if (block.type === "callout") {
    return (
      <div className="border-l-4 border-zinc-500 bg-zinc-900 px-5 py-4">
        <p className="text-sm font-medium text-zinc-400">
          {block.variant || "Note"}
        </p>

        <p className="mt-2 leading-7 text-zinc-300">{block.content}</p>
      </div>
    );
  }

  // ASCII diagram
  if (block.type === "ascii_diagram") {
    return (
      <pre className="overflow-x-auto rounded-lg bg-black p-5 text-sm leading-6 text-zinc-300">
        {block.content}
      </pre>
    );
  }

  // Table
  if (block.type === "table") {
    const rows = block.content.split("\n").filter((row) => row.trim());

    return (
      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full text-left text-sm">
          <tbody>
            {rows.map((row, index) => {
              const cells = row
                .split("|")
                .map((cell) => cell.trim())
                .filter(Boolean);

              return (
                <tr
                  key={index}
                  className="border-b border-zinc-800 last:border-b-0"
                >
                  {cells.map((cell, cellIndex) => (
                    <td key={cellIndex} className="px-4 py-3 text-zinc-300">
                      {cell}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  return null;
}
