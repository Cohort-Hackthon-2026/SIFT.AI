import { FileText, ExternalLink, Image as ImageIcon, MapPin, MessageSquareQuote, Sparkles } from "lucide-react";
import { useCitation } from "../../../store/citation";

function CitationBadge({ citation }) {
  const openCitation = useCitation((state) => state.openCitation);

  if (!citation) return null;

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
    rawDocId.startsWith("chat-text-");

  const isImage = citation.source === "image";
  const hasBoxes = citation.bounding_boxes && citation.bounding_boxes.length > 0;

  const docName = isChatText
    ? "Human Statement Evidence"
    : citation.document || citation.title || "Legal Authority";
  const pageNum = isChatText ? null : (citation.page || citation.page_number);

  return (
    <button
      type="button"
      onClick={() => openCitation(citation)}
      className={`group flex items-center gap-2 rounded-xl border px-3 py-1.5 text-left text-xs transition active:scale-98 ${
        isChatText
          ? "border-amber-500/30 bg-amber-500/5 hover:border-amber-500 hover:bg-amber-500/10 text-text"
          : "border-border bg-background/80 hover:border-primary hover:bg-primary/5 text-text hover:shadow-xs"
      }`}
      title={`Inspect ${docName}${pageNum ? ` (Page ${pageNum})` : ""}`}
    >
      <div
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border group-hover:scale-105 transition ${
          isChatText
            ? "bg-amber-500/15 border-amber-500/30 text-amber-600 dark:text-amber-400"
            : isWeb
            ? "bg-sky-500/10 border-sky-500/20 text-sky-600 dark:text-sky-400"
            : isImage
            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400"
            : "bg-surface border-border/80 text-primary group-hover:border-primary/40"
        }`}
      >
        {isWeb ? (
          <ExternalLink size={12} />
        ) : isChatText ? (
          <MessageSquareQuote size={12} />
        ) : isImage ? (
          <ImageIcon size={12} />
        ) : (
          <FileText size={12} />
        )}
      </div>

      <div className="min-w-0 flex-1 flex items-center gap-1.5">
        <span
          className={`truncate font-semibold transition max-w-[180px] sm:max-w-[240px] ${
            isChatText
              ? "text-text group-hover:text-amber-600 dark:group-hover:text-amber-400"
              : "text-text group-hover:text-primary"
          }`}
        >
          {docName}
        </span>
        {isChatText && (
          <span className="flex items-center gap-0.5 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-bold text-amber-700 dark:text-amber-300 border border-amber-500/20">
            <Sparkles size={9} />
            Exact Statement
          </span>
        )}
        {pageNum && (
          <span className="rounded bg-surface px-1.5 py-0.5 text-[10px] font-mono text-textMuted border border-border/60">
            p.{pageNum}
          </span>
        )}
        {hasBoxes && (
          <span className="hidden sm:flex items-center gap-0.5 text-[10px] text-primary font-medium" title="Bounding box coordinates available">
            <MapPin size={10} />
          </span>
        )}
      </div>
    </button>
  );
}

export default CitationBadge;