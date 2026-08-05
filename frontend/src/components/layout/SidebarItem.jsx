import { MessageSquareText, Trash2 } from "lucide-react";

function SidebarItem({ chat, isActive, onSelect, onDelete }) {
  return (
    <div className={`group flex items-center gap-2 rounded-2xl border px-3 py-3 transition ${isActive ? "border-primary/40 bg-primary/10" : "border-transparent bg-transparent hover:border-border hover:bg-background"}`}>
      <button
        type="button"
        onClick={onSelect}
        className="flex min-w-0 flex-1 items-center gap-2 text-left"
      >
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${isActive ? "bg-primary text-textInverse" : "bg-background text-textMuted"}`}>
          <MessageSquareText size={16} />
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text">{chat.title || "New Research Chat"}</p>
          <p className="truncate text-xs text-textMuted">{chat.mode || "STRICT"}</p>
        </div>
      </button>

      <button
        type="button"
        onClick={onDelete}
        className="rounded-xl p-2 text-textMuted transition hover:bg-surface hover:text-text"
        aria-label={`Delete ${chat.title || "chat"}`}
      >
        <Trash2 size={15} />
      </button>
    </div>
  );
}

export default SidebarItem;
