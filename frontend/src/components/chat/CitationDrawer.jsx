import { X, Scale, FileText } from "lucide-react";
import CitationCard from "./CitationCard";
import { useCitation } from "../../../store/citation";

function CitationDrawer() {
  const open = useCitation((state) => state.open);
  const citation = useCitation((state) => state.citation);
  const closeCitation = useCitation((state) => state.closeCitation);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm transition-opacity"
      onClick={(e) => {
        if (e.target === e.currentTarget) closeCitation();
      }}
    >
      <div className="absolute right-0 top-0 h-screen w-full max-w-xl border-l border-border bg-surface shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
        <div className="flex items-center justify-between border-b border-border p-5 bg-background/50">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Scale size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-text">Legal Evidence & Authority</h2>
              <p className="text-xs text-textMuted">SIFT.AI Grounding Coordinates & Source Inspection</p>
            </div>
          </div>

          <button
            type="button"
            onClick={closeCitation}
            className="flex h-8 w-8 items-center justify-center rounded-xl border border-border text-textMuted hover:bg-background hover:text-text transition"
            aria-label="Close evidence panel"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 sm:p-6">
          <CitationCard citation={citation} />
        </div>
      </div>
    </div>
  );
}

export default CitationDrawer;

