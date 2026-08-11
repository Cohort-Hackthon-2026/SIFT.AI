import { useEffect, useState } from "react";
import { Plus, MessageSquare, PanelLeftClose } from "lucide-react";
import { useAuth, useClerk, useUser } from "@clerk/react";

import Button from "../ui/Button";
import SidebarItem from "./SidebarItem";
import SidebarFooter from "./SidebarFooter";

import { useChat } from "../../../store/chat";
import { useDocuments } from "../../../store/documents";

function Sidebar({ isOpen, onClose }) {
  const [isSigningOut, setIsSigningOut] = useState(false);

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

  useEffect(() => {
    if (isSignedIn) {
      void loadChats();
    } else {
      useChat.getState().setChats([]);
      useChat.getState().setActiveChatId(null);
      useChat.getState().clearMessages();
    }
  }, [isSignedIn, loadChats]);

  const handleNewChat = async () => {
    if (!isSignedIn) {
      useChat.getState().setActiveChatId(null);
      useChat.getState().clearMessages();
      useChat.getState().setInput("");
      onClose?.();
      return;
    }
    try {
      await createNewChat("New Research Chat");
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
              {documents.length} document{documents.length !== 1 ? "s" : ""} loaded
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

        <div className="flex-1 overflow-y-auto px-4 py-4">
          <Button
            variant="primary"
            className="mb-4 flex w-full items-center justify-center gap-2 transition-all"
            onClick={handleNewChat}
          >
            <Plus size={18} />
            New chat
          </Button>

          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-textMuted">
            <MessageSquare size={14} />
            Recent chats
          </div>

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

          {error && (
            <p className="mt-4 rounded-xl bg-error/10 p-3 text-sm text-error border border-error/20">
              {error}
            </p>
          )}
        </div>

        {isSignedIn && <SidebarFooter email={email} imageUrl={user?.imageUrl} onLogout={handleLogout} isSigningOut={isSigningOut} />}
      </aside>

      {isOpen && (
        <div className="fixed inset-0 z-30 bg-overlay lg:hidden pointer-events-auto" />
      )}
    </>
  );
}

export default Sidebar;
