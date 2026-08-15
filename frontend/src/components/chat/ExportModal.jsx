import { useState } from "react";
import { FileText, Download, X, FileCheck, Presentation, Loader2 } from "lucide-react";
import { api } from "../../lib/api";

function ExportModal({ chatId, chatTitle, isOpen, onClose }) {
  const [format, setFormat] = useState("PDF");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleExport = async () => {
    if (!chatId) {
      window.addToast?.("No active chat session to export.", "error");
      return;
    }

    setLoading(true);
    try {
      const blob = await api.exportChat(chatId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const cleanTitle = (chatTitle || "Legal_Research_Memo")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .slice(0, 40);
      const ext = format.toLowerCase();
      a.download = `${cleanTitle}_${new Date().toISOString().slice(0, 10)}.${ext}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
      window.addToast?.(`Exported ${format} memo successfully.`, "success");
      onClose();
    } catch (err) {
      if (err.status === 402 || err.tierGate) {
        window.addToast?.(`${format} export requires an upgraded tier.`, "warning", 5000);
      } else {
        window.addToast?.(`Export failed: ${err.message || String(err)}`, "error", 5000);
      }
    } finally {
      setLoading(false);
    }
  };

  const formats = [
    {
      id: "PDF",
      title: "Chambers Legal Memo (PDF)",
      description: "Formal letterhead, Executive Summary, Question Presented, Findings, and Table of Authorities.",
      icon: FileText,
      badge: "Universal",
      badgeColor: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    },
    {
      id: "DOCX",
      title: "Redline Brief (Word DOCX)",
      description: "Formatted Microsoft Word document with editable headings, tables, and citations.",
      icon: FileCheck,
      badge: "Starter+",
      badgeColor: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    },
    {
      id: "PPTX",
      title: "Client Pitch Deck (PowerPoint)",
      description: "Structured slide presentation for executive client briefings and partners.",
      icon: Presentation,
      badge: "Pro",
      badgeColor: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
    },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose(); }}
    >
      <div className="w-full max-w-lg rounded-3xl border border-border bg-surface p-6 sm:p-8 shadow-2xl transition-all">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Download size={22} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-text">Export Research Memo</h2>
              <p className="text-xs text-textMuted">Official chambers-ready deliverable</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-2 text-textMuted hover:bg-background hover:text-text transition"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Format Selection Cards */}
        <div className="mt-5 space-y-3">
          {formats.map((item) => {
            const Icon = item.icon;
            const isSelected = format === item.id;
            return (
              <div
                key={item.id}
                onClick={() => setFormat(item.id)}
                className={`cursor-pointer rounded-2xl border p-4 transition-all ${
                  isSelected
                    ? "border-primary bg-primary/5 ring-2 ring-primary/20 shadow-sm"
                    : "border-border bg-background hover:border-primary/50"
                }`}
              >
                <div className="flex items-start gap-3.5">
                  <div
                    className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl transition ${
                      isSelected ? "bg-primary text-textInverse" : "bg-surface text-textMuted"
                    }`}
                  >
                    <Icon size={18} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-text">{item.title}</p>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${item.badgeColor}`}>
                        {item.badge}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-textMuted">{item.description}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex items-center justify-end gap-3 pt-4 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-text hover:bg-background transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-textInverse shadow-lg shadow-primary/25 hover:bg-primary/90 transition active:scale-95 disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Generating Memo...</span>
              </>
            ) : (
              <>
                <Download size={16} />
                <span>Download {format}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExportModal;
