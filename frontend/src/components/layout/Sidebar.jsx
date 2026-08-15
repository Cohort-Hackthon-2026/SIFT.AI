import { useEffect, useState } from "react";
import {
  Plus,
  MessageSquare,
  PanelLeftClose,
  Settings,
  Zap,
  Briefcase,
  ChevronDown,
  ChevronRight,
  FolderPlus,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth, useClerk, useUser } from "@clerk/react";

import Button from "../ui/Button";
import SidebarItem from "./SidebarItem";
import SidebarFooter from "./SidebarFooter";

import { useChat } from "../../../store/chat";
import { useDocuments } from "../../../store/documents";
import { useMatters } from "../../../store/matters";
import { useUI } from "../../../store/ui";
import { useBilling } from "../../../store/billing";

function Sidebar({ isOpen, onClose }) {
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [mattersExpanded, setMattersExpanded] = useState(true);
  const [chatsExpanded, setChatsExpanded] = useState(true);
  const [showNewMatterModal, setShowNewMatterModal] = useState(false);
  const [newMatterTitle, setNewMatterTitle] = useState("");
  const [newMatterClient, setNewMatterClient] = useState("");
  const navigate = useNavigate();

  const { isSignedIn } = useAuth();
  const { signOut } = useClerk();
  const { user } = useUser();

  const chats = useChat((state) => state.chats);
  const activeChatId = useChat((state) => state.activeChatId);
  const isLoadingChats = useChat((state) => state.isLoadingChats);
  const loadChats = useChat((state) => state.loadChats);
  const createNewChat = useChat((state) => state.createNewChat);
  const selectChat = useChat((state) => state.selectChat);
  const deleteChat = useChat((state) => state.deleteChat);
  const error = useChat((state) => state.error);
  const documents = useDocuments((state) => state.documents);
  const { openBillingModal } = useUI();
  const { plan, fetchPlan } = useBilling();

  const matters = useMatters((state) => state.matters);
  const activeMatterId = useMatters((state) => state.activeMatterId);
  const fetchMatters = useMatters((state) => state.fetchMatters);
  const selectMatter = useMatters((state) => state.selectMatter);
  const createMatter = useMatters((state) => state.createMatter);

  useEffect(() => {
    if (isSignedIn) {
      void loadChats();
      void fetchMatters();
      if (!plan) {
        fetchPlan().catch(() => {});
      }
    } else {
      useChat.getState().setChats([]);
      useChat.getState().setActiveChatId(null);
      useChat.getState().clearMessages();
    }
  }, [isSignedIn, loadChats, fetchMatters, fetchPlan, plan]);

  const handleNewChat = async () => {
    if (!isSignedIn) {
      useChat.getState().setActiveChatId(null);
      useChat.getState().clearMessages();
      useChat.getState().setInput("");
      navigate("/");
      onClose?.();
      return;
    }
    try {
      await createNewChat("New Research Chat");
      navigate("/");
      onClose?.();
    } catch {
      // error handled in store
    }
  };

  const handleCreateMatter = async (e) => {
    e.preventDefault();
    if (!newMatterTitle.trim()) return;
    try {
      await createMatter({
        title: newMatterTitle.trim(),
        client_name: newMatterClient.trim() || undefined,
      });
      setNewMatterTitle("");
      setNewMatterClient("");
      setShowNewMatterModal(false);
    } catch {
      // error handled in store
    }
  };

  const handleLogout = async () => {
    setIsSigningOut(true);
    try {
      await signOut();
    } finally {
      setIsSigningOut(false);
    }
  };

  const email = user?.emailAddresses?.[0]?.emailAddress || "Signed in";

  return (
    <>
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-80 flex-col border-r border-border bg-surface/95 backdrop-blur-xl transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-5">
          <div>
            <p className="text-sm font-semibold text-text">Workspace</p>
            <p className="mt-1 text-xs text-textMuted">
              {documents.length} document{documents.length !== 1 ? "s" : ""}{" "}
              loaded
            </p>
          </div>

          <button
            type="button"
            onClick={() => onClose?.()}
            className="rounded-xl p-2 text-textMuted transition hover:bg-background hover:text-text"
            aria-label="Close sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
          <Button
            variant="primary"
            className="flex w-full items-center justify-center gap-2 transition-all shadow-md shadow-primary/20"
            onClick={handleNewChat}
          >
            <Plus size={18} />
            New research chat
          </Button>

          {/* Matters & Cases Section */}
          {isSignedIn && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setMattersExpanded((v) => !v)}
                  className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-textMuted hover:text-text transition"
                >
                  {mattersExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  <Briefcase size={14} className="text-primary" />
                  <span>Matters & Cases ({matters.length})</span>
                </button>

                <button
                  type="button"
                  onClick={() => setShowNewMatterModal(true)}
                  className="rounded-lg p-1 text-textMuted hover:bg-background hover:text-primary transition"
                  title="Create new matter"
                >
                  <FolderPlus size={15} />
                </button>
              </div>

              {mattersExpanded && (
                <div className="space-y-1 pl-1">
                  {matters.length > 0 ? (
                    matters.map((matter) => (
                      <button
                        key={matter.matter_id}
                        type="button"
                        onClick={() => selectMatter(matter.matter_id === activeMatterId ? null : matter.matter_id)}
                        className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-xs font-medium transition ${
                          activeMatterId === matter.matter_id
                            ? "bg-primary/10 text-primary font-semibold border border-primary/20"
                            : "text-text hover:bg-background"
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <p className="truncate">{matter.title}</p>
                          {matter.client_name && (
                            <p className="truncate text-[10px] text-textMuted">{matter.client_name}</p>
                          )}
                        </div>
                        <span className="text-[10px] uppercase text-textMuted px-1 rounded bg-surface">
                          {matter.practice_area || "Case"}
                        </span>
                      </button>
                    ))
                  ) : (
                    <div className="rounded-xl border border-dashed border-border p-2.5 text-center text-xs text-textMuted">
                      No chambers matters created yet.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Research Chats Section */}
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setChatsExpanded((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-textMuted hover:text-text transition"
            >
              {chatsExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              <MessageSquare size={14} />
              <span>Recent chats ({chats.length})</span>
            </button>

            {chatsExpanded && (
              <>
                {isLoadingChats ? (
                  <div className="rounded-2xl border border-border bg-background/50 p-3 text-sm text-textMuted">
                    Loading chats...
                  </div>
                ) : chats.length > 0 ? (
                  <div className="space-y-1.5">
                    {chats.map((chat) => (
                      <SidebarItem
                        key={chat.chat_id}
                        chat={chat}
                        isActive={chat.chat_id === activeChatId}
                        onSelect={() => {
                          navigate("/");
                          void selectChat(chat.chat_id);
                          onClose?.();
                        }}
                        onDelete={() => {
                          void deleteChat(chat.chat_id);
                        }}
                      />
                    ))}
                  </div>
                ) : isSignedIn ? (
                  <div className="rounded-2xl border border-border bg-background/50 p-3 text-sm text-textMuted">
                    No chats yet. Start a new research thread.
                  </div>
                ) : (
                  <div className="rounded-2xl border border-border bg-background/50 p-4 text-sm text-textMuted">
                    Sign in to save and access your recent chats.
                  </div>
                )}
              </>
            )}
          </div>

          {error && (
            <p className="mt-4 rounded-xl bg-error/10 p-3 text-sm text-error border border-error/20">
              {error}
            </p>
          )}
        </div>

        {/* Footer controls */}
        <div className="shrink-0 border-t border-border bg-surface/95 px-4 py-3 backdrop-blur-xl space-y-2">
          <button
            type="button"
            onClick={() => {
              navigate("/settings");
              onClose?.();
            }}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-textMuted transition hover:bg-background hover:text-text"
          >
            <Settings size={18} />
            Settings & Privacy
          </button>

          {isSignedIn && (plan?.tier === "FREE" || !plan?.tier) && (
            <button
              type="button"
              onClick={() => {
                openBillingModal();
                onClose?.();
              }}
              className="flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium bg-primary text-textInverse shadow-md shadow-primary/20 transition hover:opacity-90 active:scale-98"
            >
              <Zap size={16} />
              Upgrade Plan
            </button>
          )}
        </div>

        {isSignedIn && (
          <SidebarFooter
            email={email}
            imageUrl={user?.imageUrl}
            onLogout={handleLogout}
            isSigningOut={isSigningOut}
          />
        )}
      </aside>

      {/* New Matter Modal */}
      {showNewMatterModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setShowNewMatterModal(false); }}
        >
          <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-base font-bold text-text">Create Chambers Matter</h3>
              <button
                type="button"
                onClick={() => setShowNewMatterModal(false)}
                className="flex items-center justify-center h-8 w-8 rounded-lg border border-border text-textMuted hover:bg-background hover:text-text transition"
                aria-label="Close"
              >
                <X size={14} />
              </button>
            </div>
            <p className="text-xs text-textMuted mb-4">Group research documents, citations, and chats under a case.</p>
            <form onSubmit={handleCreateMatter} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Matter / Suit Title *</label>
                <input
                  type="text"
                  required
                  value={newMatterTitle}
                  onChange={(e) => setNewMatterTitle(e.target.value)}
                  placeholder="e.g. Suit No. FHC/L/CS/2026 — Zenith Bank v. FIRS"
                  className="w-full rounded-xl border border-border bg-background p-2.5 text-sm text-text outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text mb-1">Client Name (Optional)</label>
                <input
                  type="text"
                  value={newMatterClient}
                  onChange={(e) => setNewMatterClient(e.target.value)}
                  placeholder="e.g. Zenith Bank Plc"
                  className="w-full rounded-xl border border-border bg-background p-2.5 text-sm text-text outline-none focus:border-primary"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewMatterModal(false)}
                  className="rounded-xl border border-border px-3 py-1.5 text-xs font-medium text-text hover:bg-background"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-primary px-4 py-1.5 text-xs font-semibold text-textInverse shadow-sm hover:opacity-90"
                >
                  Create Matter
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isOpen && (
        <div
          onClick={() => onClose?.()}
          className="fixed inset-0 z-30 bg-overlay lg:hidden pointer-events-auto"
        />
      )}
    </>
  );
}

export default Sidebar;
