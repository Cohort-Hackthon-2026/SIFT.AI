import { useState } from "react";
import {
  FileText,
  ExternalLink,
  MessageSquareQuote,
  Image as ImageIcon,
  Eye,
  FileCode2,
  Sparkles,
} from "lucide-react";
import PdfHighlightViewer from "./PdfHighlightViewer";
import TextGroundingViewer from "./TextGroundingViewer";

function CitationCard({ citation }) {
  if (!citation) return null;

  const [activeTab, setActiveTab] = useState("viewer"); // "viewer" | "text"

  const rawDocId = String(citation.document_id || "");
  const rawDocName = citation.document || citation.document_name || "";

  const isWeb = citation.source === "web" || (!citation.document_id && citation.url);
  const isChatText =
    citation.source === "chat_text" ||
    citation.source === "text" ||
    citation.source === "user_text" ||
    rawDocName === "Chat Context" ||
    rawDocName === "User Text Statement" ||
    rawDocName === "User Statement & Incident Context" ||
    rawDocId.startsWith("chat-text-") ||
    (!citation.document_id && !citation.url && !citation.file_url);

  const isImage = citation.source === "image";
  const isPdf = !isWeb && !isChatText && !isImage && citation.document_id && !rawDocId.startsWith("chat-text-");

  const rawTextContent =
    citation.content ||
    citation.text ||
    citation.highlights ||
    citation.statement ||
    "";

  return (
    <div className="space-y-4">
      {/* Header Info */}
      <div className="rounded-2xl border border-border bg-background p-4 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-xl flex-shrink-0 ${
                isChatText
                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                  : isImage
                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                  : isWeb
                  ? "bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20"
                  : "bg-primary/10 text-primary border border-primary/20"
              }`}
            >
              {isWeb ? (
                <ExternalLink size={20} />
              ) : isChatText ? (
                <MessageSquareQuote size={20} />
              ) : isImage ? (
                <ImageIcon size={20} />
              ) : (
                <FileText size={20} />
              )}
            </div>
            <div className="min-w-0">
              <h3 className="truncate text-base font-bold text-text">
                {isChatText
                  ? "Human Text Statement & Incident Evidence"
                  : citation.document || citation.title || "Legal Authority"}
              </h3>
              <p className="text-xs text-textMuted flex items-center gap-1.5 mt-0.5">
                {isWeb ? (
                  <span>Web Precedent Authority ({citation.domain || "Online Legal Source"})</span>
                ) : isChatText ? (
                  <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                    <Sparkles size={11} />
                    Direct Human Text Input Grounding
                  </span>
                ) : isImage ? (
                  <span>OCR-Extracted Document Image</span>
                ) : (
                  <span>
                    Uploaded PDF Document · <strong className="text-text">Page {citation.page || citation.page_number || 1}</strong>
                  </span>
                )}
              </p>
            </div>
          </div>

          {isWeb && citation.url && (
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-semibold text-sky-600 dark:text-sky-400 hover:bg-sky-500/20 transition"
            >
              <span>Visit Precedent</span>
              <ExternalLink size={12} />
            </a>
          )}
        </div>
      </div>

      {/* Human Text Statement Grounding View */}
      {isChatText && (
        <TextGroundingViewer
          rawText={rawTextContent}
          initialStatement={citation.statement || ""}
          title={citation.document || "User Statement"}
        />
      )}

      {/* Tabs for PDF (Canvas Viewer vs Text Excerpt) */}
      {isPdf && (
        <div className="flex gap-2 border-b border-border pb-2 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab("viewer")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${
              activeTab === "viewer"
                ? "bg-primary text-textInverse shadow-sm"
                : "text-textMuted hover:bg-background hover:text-text"
            }`}
          >
            <Eye size={14} />
            <span>PDF Coordinate Viewer</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("text")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${
              activeTab === "text"
                ? "bg-primary text-textInverse shadow-sm"
                : "text-textMuted hover:bg-background hover:text-text"
            }`}
          >
            <FileCode2 size={14} />
            <span>Extracted Chunk Text</span>
          </button>
        </div>
      )}

      {/* PDF Highlight Viewer */}
      {isPdf && activeTab === "viewer" && (
        <PdfHighlightViewer
          documentId={citation.document_id}
          documentName={citation.document}
          pageNumber={citation.page || citation.page_number || 1}
          boundingBoxes={citation.bounding_boxes || []}
        />
      )}

      {/* Text Excerpt (for Web, Image, or PDF fallback tab) */}
      {!isChatText && (!isPdf || activeTab === "text") && (
        <div className="rounded-2xl border border-border bg-background p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-textMuted mb-2">
            Cited Evidence Chunk
          </p>
          <div className="max-h-72 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-text font-serif bg-surface/50 p-3 rounded-xl border border-border/50">
            {rawTextContent || "No raw text excerpt available."}
          </div>
        </div>
      )}
    </div>
  );
}

export default CitationCard;