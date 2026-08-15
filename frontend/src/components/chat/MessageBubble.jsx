import React, { useState } from "react";
import { Bot, AlertTriangle, ShieldCheck, ChevronDown, ChevronUp, Scale, Sparkles } from "lucide-react";

import CitationBadge from "./CitationBadge";
import MarkdownRenderer from "./MarkdownRenderer";
import ChatActions from "./ChatActions";
import { useCitation } from "../../../store/citation";

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  const [conflictExpanded, setConflictExpanded] = useState(true);
  const openCitation = useCitation((state) => state.openCitation);

  const conflict = message.conflictAlert;
  const hasConflict = Boolean(conflict && conflict.has_conflict);

  const severityColor =
    conflict?.severity === "HIGH"
      ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30"
      : conflict?.severity === "MEDIUM"
      ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
      : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30";

  const confidencePct = conflict?.confidence_score
    ? Math.round(Number(conflict.confidence_score) * 100)
    : null;

  return (
    <>
      <div className={`flex gap-3 sm:gap-4 ${isUser ? "justify-end" : "justify-start"}`}>
        {!isUser && (
          <div className="h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary text-textInverse shadow-md hidden sm:flex">
            <Bot size={20} />
          </div>
        )}

        <div
          className={`max-w-full sm:max-w-[88%] rounded-3xl border p-4 sm:p-6 transition-colors break-words ${
            isUser
              ? "bg-primary text-textInverse border-primary/40 shadow-md"
              : message.error
              ? "bg-error/10 text-text border-error/40"
              : "bg-surface text-text border-border shadow-sm"
          }`}
        >
          {/* User Attached Images Preview */}
          {isUser && message.images && message.images.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {message.images.map((imgSrc, i) => (
                <img
                  key={i}
                  src={imgSrc.startsWith("data:") ? imgSrc : `data:image/jpeg;base64,${imgSrc}`}
                  alt="Attached evidence"
                  className="h-20 w-20 rounded-xl object-cover border border-white/20 shadow-sm"
                />
              ))}
            </div>
          )}

          {message.error ? (
            <div className="space-y-3">
              <div className="text-sm font-semibold text-error">Error</div>
              <div className="text-sm text-error/90 whitespace-pre-wrap">{message.content}</div>
            </div>
          ) : (
            <>
              <MarkdownRenderer className={isUser ? "" : "text-justify"}>
                {message.content}
              </MarkdownRenderer>

              {/* High-Visibility Legal Conflict Card */}
              {hasConflict && (
                <div className="mt-5 overflow-hidden rounded-2xl border border-rose-500/30 bg-rose-500/5 dark:bg-rose-950/20 shadow-sm">
                  <div
                    onClick={() => setConflictExpanded((v) => !v)}
                    className="flex cursor-pointer items-center justify-between gap-3 border-b border-rose-500/20 bg-rose-500/10 p-3.5 sm:px-4"
                  >
                    <div className="flex items-center gap-2.5">
                      <AlertTriangle size={18} className="text-rose-600 dark:text-rose-400 flex-shrink-0" />
                      <span className="font-bold text-sm text-rose-700 dark:text-rose-300 tracking-tight">
                        Legal Conflict & Precedent Risk Detected
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase ${severityColor}`}>
                        {conflict.severity || "HIGH"} Severity
                      </span>
                      {confidencePct && (
                        <span className="rounded-full bg-surface border border-border px-2 py-0.5 text-[10px] font-semibold text-textMuted">
                          {confidencePct}% Confidence
                        </span>
                      )}
                      <button type="button" className="text-textMuted hover:text-text p-0.5">
                        {conflictExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                  </div>

                  {conflictExpanded && (
                    <div className="p-4 sm:p-5 space-y-4 text-xs sm:text-sm">
                      <p className="text-text font-medium leading-relaxed">
                        {conflict.explanation}
                      </p>

                      {/* Side-by-side Comparison Grid */}
                      {(conflict.contract_clause || conflict.legal_precedent) && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                          {conflict.contract_clause && (
                            <div className="rounded-xl border border-border bg-surface p-3 space-y-1.5">
                              <p className="text-[11px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 flex items-center gap-1">
                                <Scale size={13} /> Internal Contract Clause
                              </p>
                              <p className="text-text font-serif italic text-xs sm:text-sm leading-relaxed">
                                "{conflict.contract_clause}"
                              </p>
                            </div>
                          )}

                          {conflict.legal_precedent && (
                            <div className="rounded-xl border border-border bg-surface p-3 space-y-1.5">
                              <p className="text-[11px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 flex items-center gap-1">
                                <Sparkles size={13} /> Live Precedent / Statutory Cap
                              </p>
                              <p className="text-text font-serif italic text-xs sm:text-sm leading-relaxed">
                                "{conflict.legal_precedent}"
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Verify Before You Rely Affordance */}
                      <div className="flex items-center justify-between pt-2 border-t border-rose-500/10">
                        <span className="text-[11px] text-textMuted flex items-center gap-1">
                          <ShieldCheck size={13} className="text-emerald-500" />
                          Verify against primary legal authorities before client advisory.
                        </span>
                        {message.citations && message.citations.length > 0 && (
                          <button
                            type="button"
                            onClick={() => openCitation(message.citations[0])}
                            className="rounded-lg bg-surface border border-border px-2.5 py-1 text-xs font-semibold text-text hover:border-primary hover:text-primary transition"
                          >
                            Inspect Coordinates
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Citations List */}
              {!isUser && message.citations && message.citations.length > 0 && (
                <div className="mt-5 pt-4 border-t border-border/60">
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-textMuted mb-2.5">
                    <Scale size={13} className="text-primary" />
                    <span>Cited Legal Authorities & Evidence ({message.citations.length})</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {message.citations.map((citation, index) => (
                      <CitationBadge
                        key={`${citation.chunk_id || citation.url || index}`}
                        citation={citation}
                      />
                    ))}
                  </div>
                </div>
              )}

              {!isUser && <ChatActions text={message.content} />}
            </>
          )}
        </div>
      </div>

      {isUser && (
        <div className="flex gap-1 sm:gap-2 justify-end mt-1">
          <ChatActions text={message.content} isCompact={true} />
        </div>
      )}
    </>
  );
}

export default MessageBubble;
