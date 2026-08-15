import React, { useState, useMemo } from "react";
import {
  MessageSquareQuote,
  Quote,
  Copy,
  Check,
  Search,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  FileText,
  Highlighter,
  Info,
} from "lucide-react";

/**
 * Splits raw human text into structured sentences / statements
 * with exact character offsets and metadata.
 */
function segmentTextIntoStatements(rawText) {
  if (!rawText || typeof rawText !== "string") return [];

  // Match sentences ending with ., ?, !, or newlines
  const regex = /([^.?!;\n]+[.?!;]?)/g;
  const matches = [];
  let match;

  while ((match = regex.exec(rawText)) !== null) {
    const text = match[0].trim();
    if (text.length > 0) {
      const start = match.index;
      const end = start + match[0].length;
      const words = text.split(/\s+/).filter(Boolean).length;
      matches.push({
        id: matches.length,
        text,
        start,
        end,
        words,
      });
    }
  }

  return matches;
}

export default function TextGroundingViewer({
  rawText = "",
  initialStatement = "",
  title = "User Statement Context",
}) {
  const [copiedStatement, setCopiedStatement] = useState(false);
  const [copiedAll, setCopiedAll] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const statements = useMemo(() => segmentTextIntoStatements(rawText), [rawText]);

  // Find initial active statement (either matching initialStatement, or first statement)
  const initialIndex = useMemo(() => {
    if (!statements.length) return 0;
    if (initialStatement) {
      const matchIdx = statements.findIndex(
        (s) =>
          s.text.toLowerCase().includes(initialStatement.toLowerCase()) ||
          initialStatement.toLowerCase().includes(s.text.toLowerCase())
      );
      if (matchIdx !== -1) return matchIdx;
    }
    return 0;
  }, [statements, initialStatement]);

  const [activeIndex, setActiveIndex] = useState(initialIndex);

  const activeStatement = statements[activeIndex] || statements[0] || null;

  const totalWords = useMemo(
    () => (rawText ? rawText.split(/\s+/).filter(Boolean).length : 0),
    [rawText]
  );

  const handleCopyStatement = () => {
    if (!activeStatement) return;
    navigator.clipboard.writeText(activeStatement.text);
    setCopiedStatement(true);
    setTimeout(() => setCopiedStatement(false), 2000);
  };

  const handleCopyAll = () => {
    if (!rawText) return;
    navigator.clipboard.writeText(rawText);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  const handlePrev = () => {
    if (activeIndex > 0) setActiveIndex(activeIndex - 1);
  };

  const handleNext = () => {
    if (activeIndex < statements.length - 1) setActiveIndex(activeIndex + 1);
  };

  if (!rawText || rawText.trim() === "") {
    return (
      <div className="rounded-2xl border border-border bg-background p-6 text-center space-y-3">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
          <MessageSquareQuote size={24} />
        </div>
        <h4 className="text-sm font-bold text-text">User Statement Evidence</h4>
        <p className="text-xs text-textMuted max-w-sm mx-auto">
          This citation was grounded directly on the conversational text and factual statements submitted in the chat.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Overview Card */}
      <div className="rounded-2xl border border-border bg-background/80 p-4 shadow-sm backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <Sparkles size={18} />
            </div>
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                Grounding Analysis
              </span>
              <h4 className="text-sm font-bold text-text">Exact Statement Isolation</h4>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[11px] text-textMuted font-mono">
            <span className="rounded-lg bg-surface px-2 py-1 border border-border/80">
              {statements.length} {statements.length === 1 ? "statement" : "statements"}
            </span>
            <span className="rounded-lg bg-surface px-2 py-1 border border-border/80">
              {totalWords} words
            </span>
          </div>
        </div>
      </div>

      {/* Hero: Narrowed Exact Statement Card */}
      {activeStatement && (
        <div className="relative overflow-hidden rounded-2xl border-2 border-amber-500/40 bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-transparent p-5 shadow-md">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[11px] font-bold text-amber-700 dark:text-amber-300 border border-amber-500/30">
                <Quote size={11} />
                Statement #{activeIndex + 1} of {statements.length}
              </span>
              <span className="text-[11px] font-mono text-textMuted">
                {activeStatement.words} words · Chars {activeStatement.start}–{activeStatement.end}
              </span>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handlePrev}
                disabled={activeIndex === 0}
                className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-background text-text disabled:opacity-30 hover:bg-surface transition"
                title="Previous statement"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                type="button"
                onClick={handleNext}
                disabled={activeIndex === statements.length - 1}
                className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-background text-text disabled:opacity-30 hover:bg-surface transition"
                title="Next statement"
              >
                <ChevronRight size={14} />
              </button>
              <button
                type="button"
                onClick={handleCopyStatement}
                className="flex items-center gap-1 rounded-lg border border-amber-500/30 bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300 hover:bg-amber-500/25 transition ml-1"
                title="Copy verbatim statement"
              >
                {copiedStatement ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                <span>{copiedStatement ? "Copied" : "Copy Statement"}</span>
              </button>
            </div>
          </div>

          <div className="relative">
            <Quote
              size={36}
              className="absolute -left-1 -top-2 text-amber-500/20 -z-0 pointer-events-none select-none"
            />
            <p className="relative z-10 text-sm sm:text-base font-serif italic leading-relaxed text-text font-medium pl-4 border-l-2 border-amber-500">
              "{activeStatement.text}"
            </p>
          </div>
        </div>
      )}

      {/* Statement Selector Strip */}
      {statements.length > 1 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-textMuted px-1">
            <span className="font-semibold uppercase tracking-wider text-[10px]">Jump to Statement</span>
            <span>Click any statement to isolate</span>
          </div>
          <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            {statements.map((s, idx) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setActiveIndex(idx)}
                className={`group flex items-center gap-1.5 shrink-0 rounded-xl px-3 py-1.5 text-xs font-medium transition border ${
                  idx === activeIndex
                    ? "border-amber-500 bg-amber-500/15 text-amber-700 dark:text-amber-300 font-bold shadow-xs"
                    : "border-border bg-background/60 text-textMuted hover:border-border/80 hover:bg-surface hover:text-text"
                }`}
              >
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-surface text-[10px] font-mono">
                  {idx + 1}
                </span>
                <span className="max-w-[120px] truncate">{s.text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search & Filter Toolbar */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-textMuted" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search phrases or keywords in human statement..."
          className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-4 text-xs text-text placeholder-textMuted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30 transition"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchQuery("")}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md px-1.5 py-0.5 text-[10px] text-textMuted hover:bg-surface hover:text-text"
          >
            Clear
          </button>
        )}
      </div>

      {/* Full Text Document with In-Situ Illumination */}
      <div className="rounded-2xl border border-border bg-background p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-border/60 pb-2.5">
          <div className="flex items-center gap-2 text-xs font-bold text-text">
            <FileText size={14} className="text-primary" />
            <span>Full User Statement Context</span>
          </div>

          <button
            type="button"
            onClick={handleCopyAll}
            className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-[11px] font-medium text-textMuted hover:bg-surface hover:text-text transition"
          >
            {copiedAll ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
            <span>{copiedAll ? "Copied" : "Copy Full Text"}</span>
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto space-y-2 pr-1 font-serif text-sm leading-relaxed">
          {statements.map((s, idx) => {
            const isActive = idx === activeIndex;
            const isMatchSearch =
              searchQuery && s.text.toLowerCase().includes(searchQuery.toLowerCase());

            return (
              <div
                key={s.id}
                onClick={() => setActiveIndex(idx)}
                className={`group cursor-pointer rounded-xl p-2.5 transition relative border ${
                  isActive
                    ? "border-amber-500/50 bg-amber-500/10 text-text font-medium shadow-xs"
                    : isMatchSearch
                    ? "border-primary/40 bg-primary/5 text-text"
                    : "border-transparent hover:border-border hover:bg-surface/50 text-text/90"
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <span
                    className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-mono transition ${
                      isActive
                        ? "bg-amber-500 text-amber-950 font-bold"
                        : "bg-surface text-textMuted group-hover:bg-border/60"
                    }`}
                  >
                    #{idx + 1}
                  </span>
                  <p className="flex-1 whitespace-pre-wrap">
                    {s.text}
                  </p>
                </div>
                {isActive && (
                  <div className="mt-1.5 flex items-center gap-1 text-[10px] font-sans font-semibold text-amber-600 dark:text-amber-400 pl-7">
                    <Sparkles size={10} />
                    <span>Currently isolated statement</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
