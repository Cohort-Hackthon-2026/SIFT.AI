import { create } from "zustand";
import { persist } from "zustand/middleware";

import { api } from "../src/lib/api";
import { useDocuments } from "./documents";
import { useSettings } from "./settings";

const normalizeCitation = (citation) => {
  if (!citation) {
    return null;
  }

  if (citation.document_id) {
    return {
      label: `${citation.document_name || "Document"} · p${citation.page_number || 1}`,
      document: citation.document_name || "Document",
      page: citation.page_number || 1,
      content: citation.chunk_id || "",
      ...citation,
    };
  }

  if (citation.title) {
    return {
      label: citation.title,
      document: citation.domain || "Web source",
      page: null,
      content: citation.url || "",
      ...citation,
    };
  }

  return citation;
};

const normalizeMessage = (message) => ({
  id: message.message_id || message.id || crypto.randomUUID(),
  role: message.role,
  content: message.content || "",
  citations: [
    ...(message.metadata?.internal_citations || []),
    ...(message.metadata?.external_citations || []),
  ].map(normalizeCitation).filter(Boolean),
  createdAt: message.created_at,
});

const chatStore = (set, get) => ({
  input: "",
  messages: [],
  chats: [],
  activeChatId: null,
  isLoadingChats: false,
  isSending: false,
  streamStatus: "",
  error: null,

  setInput: (input) => set({ input }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  clearMessages: () => set({ messages: [] }),

  setStreaming: (value) => set({ isSending: value }),

  setActiveChatId: (activeChatId) => set({ activeChatId }),

  setChats: (chats) => set({ chats }),

  setMessages: (messages) => set({ messages }),

  createNewChat: async (title = "New Research Chat") => {
    try {
      const mode = useSettings.getState().mode || "strict";
      const chat = await api.createChat({
        title,
        mode: mode.toUpperCase(),
        document_ids: [],
      });

      set((state) => ({
        chats: [chat, ...state.chats.filter((item) => item.chat_id !== chat.chat_id)],
        activeChatId: chat.chat_id,
        messages: [],
        error: null,
      }));

      return chat;
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  loadChats: async () => {
    set({ isLoadingChats: true, error: null });

    try {
      const response = await api.listChats();
      set({ chats: response?.chats || [] });
      return response?.chats || [];
    } catch (err) {
      set({ error: err.message });
      throw err;
    } finally {
      set({ isLoadingChats: false });
    }
  },

  selectChat: async (chatId) => {
    set({ activeChatId: chatId, messages: [], error: null });

    try {
      const response = await api.listChatMessages(chatId);
      set({ messages: (response?.messages || []).map(normalizeMessage) });
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  deleteChat: async (chatId) => {
    try {
      await api.deleteChat(chatId);
      set((state) => ({
        chats: state.chats.filter((chat) => chat.chat_id !== chatId),
        activeChatId: state.activeChatId === chatId ? null : state.activeChatId,
        messages: state.activeChatId === chatId ? [] : state.messages,
      }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  sendMessage: async (content) => {
    const trimmed = content?.trim();
    if (!trimmed) {
      return null;
    }

    const documentIds = (useDocuments.getState().documents || []).map((doc) => doc.document_id);
    let chatId = get().activeChatId;

    if (!chatId) {
      const createdChat = await get().createNewChat(trimmed.slice(0, 48));
      chatId = createdChat.chat_id;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };

    const assistantMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      citations: [],
    };

    set((state) => ({
      messages: [...state.messages, userMessage, assistantMessage],
      input: "",
      isSending: true,
      error: null,
      streamStatus: "Thinking...",
    }));

    try {
      const mode = useSettings.getState().mode;
      const response = await api.streamChat({
        query: trimmed,
        chat_id: chatId,
        mode: (mode || "STRICT").toUpperCase(),
        document_ids: documentIds,
        top_k: 5,
        min_score_threshold: 0.5,
      });

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("The chat stream is unavailable.");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let assistantContent = "";
      let citations = [];

      const processEventChunk = (chunk) => {
        const eventLines = chunk.split(/\r?\n/);
        let eventName = "message";
        const dataLines = [];

        for (const line of eventLines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5));
          }
        }

        const rawData = dataLines.join("\n").trim();
        if (!rawData) {
          return;
        }

        let payload;
        try {
          payload = JSON.parse(rawData);
        } catch {
          return;
        }

        if (eventName === "message") {
          const delta = payload.delta || "";
          assistantContent += delta;
          set((state) => ({
            messages: state.messages.map((message) =>
              message.id === assistantMessage.id ? { ...message, content: assistantContent } : message
            ),
          }));
        } else if (eventName === "metadata") {
          citations = [
            ...(payload.internal_citations || []),
            ...(payload.external_citations || []),
          ].map(normalizeCitation).filter(Boolean);
          set((state) => ({
            messages: state.messages.map((message) =>
              message.id === assistantMessage.id ? { ...message, citations } : message
            ),
          }));
        } else if (eventName === "status") {
          set({ streamStatus: payload.step || "Thinking..." });
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (!part.trim()) {
            continue;
          }
          processEventChunk(part);
        }
      }

      const tail = buffer.trim();
      if (tail) {
        processEventChunk(tail);
      }

      set({ streamStatus: "Done" });

      if (!get().chats.some((chat) => chat.chat_id === chatId)) {
        await get().loadChats();
      }

      return assistantMessage;
    } catch (err) {
      let errorMessage = err.message || "An error occurred";

      if (err.detail) {
        if (typeof err.detail === "string") {
          errorMessage = err.detail;
        } else if (Array.isArray(err.detail)) {
          errorMessage = err.detail
            .map((e) => e.msg || e.message || JSON.stringify(e))
            .join("; ");
        }
      }

      set((state) => ({
        messages: state.messages.filter((message) => message.id !== assistantMessage.id),
        error: errorMessage,
      }));

      throw err;
    } finally {
      set({ isSending: false });
    }
  },
});

export const useChat = create(
  persist(chatStore, {
    name: "chat",
    partialize: (state) => ({
      chats: state.chats,
      activeChatId: state.activeChatId,
      messages: state.messages,
      input: state.input,
    }),
  })
);