import { useState, useRef, useEffect } from "react";
import { MessageSquareText, Trash2, Pencil, Check, X } from "lucide-react";

function SidebarItem({ chat, isActive, onSelect, onDelete, onRename }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(chat.title || "Legal Research");
  const inputRef = useRef(null);

  useEffect(() => {
    setEditTitle(chat.title || "Legal Research");
  }, [chat.title]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSaveRename = (e) => {
    e?.stopPropagation();
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== chat.title && onRename) {
      onRename(chat.chat_id, trimmed);
    }
    setIsEditing(false);
  };

  const handleCancelRename = (e) => {
    e?.stopPropagation();
    setEditTitle(chat.title || "Legal Research");
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      handleSaveRename(e);
    } else if (e.key === "Escape") {
      handleCancelRename(e);
    }
  };

  return (
    <div
      className={`group relative flex items-center gap-2 rounded-2xl border px-3 py-2.5 transition-all duration-200 ${
        isActive
          ? "border-primary/40 bg-primary/10 shadow-sm"
          : "border-transparent bg-transparent hover:border-border hover:bg-background/80"
      }`}
    >
      {isEditing ? (
        <div className="flex flex-1 items-center gap-1.5 py-0.5" onClick={(e) => e.stopPropagation()}>
          <input
            ref={inputRef}
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSaveRename}
            maxLength={80}
            className="flex-1 rounded-lg border border-primary bg-background px-2 py-1 text-xs font-medium text-text outline-none focus:ring-1 focus:ring-primary"
            placeholder="Chat title..."
          />
          <button
            type="button"
            onClick={handleSaveRename}
            className="rounded-lg p-1 text-primary hover:bg-primary/10 transition"
            title="Save title"
          >
            <Check size={14} />
          </button>
          <button
            type="button"
            onClick={handleCancelRename}
            className="rounded-lg p-1 text-textMuted hover:bg-background transition"
            title="Cancel"
          >
            <X size={14} />
          </button>
        </div>
      ) : (
        <>
          <button
            type="button"
            onClick={onSelect}
            className="flex min-w-0 flex-1 items-center gap-2 text-left"
          >
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition ${
                isActive ? "bg-primary text-textInverse shadow-sm" : "bg-background text-textMuted group-hover:text-text"
              }`}
            >
              <MessageSquareText size={15} />
            </div>

            <div className="min-w-0 flex-1">
              <p
                className="truncate text-xs font-semibold text-text group-hover:text-primary transition-colors"
                title={chat.title || "Legal Research"}
              >
                {chat.title || "Legal Research"}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-[10px] font-medium uppercase tracking-wider text-textMuted">
                  {chat.mode || "STRICT"}
                </span>
                {chat.matter_id && (
                  <span className="text-[9px] px-1 rounded bg-surface border border-border text-primary font-medium">
                    Matter
                  </span>
                )}
              </div>
            </div>
          </button>

          {/* Action buttons (Rename + Delete) */}
          <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity duration-150">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
              }}
              className="rounded-lg p-1.5 text-textMuted transition hover:bg-surface hover:text-text"
              aria-label={`Rename ${chat.title || "chat"}`}
              title="Rename chat"
            >
              <Pencil size={13} />
            </button>

            <button
              type="button"
              onClick={onDelete}
              className="rounded-lg p-1.5 text-textMuted transition hover:bg-surface hover:text-error"
              aria-label={`Delete ${chat.title || "chat"}`}
              title="Delete chat"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default SidebarItem;
