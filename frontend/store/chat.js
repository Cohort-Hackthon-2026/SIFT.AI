import { create } from "zustand";

import { api } from "../src/lib/api";
import { streamChatQuery } from "../src/lib/sseClient";
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
  conflictAlert: message.metadata?.conflict_alert || null,
  mode: message.metadata?.mode,
  createdAt: message.created_at,
});

const chatStore = (set, get) => ({
  input: "",
  messages: [],
  chats: [],
  activeChatId: null,
  isLoadingChats: false,
  isLoadingMessages: false,
  chatLoadVersion: 0,
  isSending: false,
  streamStatus: "",
  streamProgress: 0,
  streamSteps: [],
  error: null,

  setInput: (input) => set((state) => ({ input: typeof input === "function" ? input(state.input) : input })),

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
    set({ activeChatId: chatId, messages: [], error: null, isLoadingMessages: true });

    try {
      const response = await api.listChatMessages(chatId);
      set((state) => ({
        messages: (response?.messages || []).map(normalizeMessage),
        chatLoadVersion: state.chatLoadVersion + 1,
      }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    } finally {
      set({ isLoadingMessages: false });
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
    const assistantMessage = { id: crypto.randomUUID(), role: "assistant", content: "", citations: [] };
    let assistantMetadata = {};

    set((state) => ({
      messages: [...state.messages, userMessage],
      input: "",
      isSending: true,
      error: null,
      streamStatus: "",
      streamProgress: 0,
      streamSteps: [],
    }));

    try {
      const mode = useSettings.getState().mode;
      let assistantContent = "";
      let citations = [];
      await streamChatQuery({
        payload: {
          query: trimmed,
          chat_id: chatId,
          mode: (mode || "STRICT").toUpperCase(),
          document_ids: documentIds,
          top_k: 5,
          min_score_threshold: 0.5,
        },
        onToken: (delta) => {
          assistantContent += delta;
        },
        onMetadata: (payload) => {
          citations = [
            ...(payload.internal_citations || []),
            ...(payload.external_citations || []),
          ].map(normalizeCitation).filter(Boolean);
          assistantMetadata = { conflictAlert: payload.conflict_alert || null, mode: payload.mode };
        },
        onStatus: (payload) => {
          if (!payload?.step) return;
          set((state) => ({
            streamStatus: payload.step,
            streamProgress: Number.isFinite(payload.progress) ? payload.progress : state.streamProgress,
            streamSteps: state.streamSteps.some((item) => item.step === payload.step)
              ? state.streamSteps.map((item) => item.step === payload.step ? { ...item, progress: payload.progress } : item)
              : [...state.streamSteps, { step: payload.step, progress: payload.progress }],
          }));
        },
      });

      const completedAssistantMessage = { ...assistantMessage, content: assistantContent, citations, ...assistantMetadata };
      set((state) => ({ messages: [...state.messages, completedAssistantMessage] }));

      if (!get().chats.some((chat) => chat.chat_id === chatId)) {
        await get().loadChats();
      }

      return completedAssistantMessage;
    } catch (err) {
      // Format error message for display
      let errorMessage = err.message || "An error occurred";
      
      // Try to extract more detailed error information from API response
      if (err.detail) {
        if (typeof err.detail === "string") {
          errorMessage = err.detail;
        } else if (Array.isArray(err.detail)) {
          // Handle validation errors from Pydantic
          errorMessage = err.detail
            .map((e) => e.msg || e.message || JSON.stringify(e))
            .join("; ");
        }
      }

      // Update assistant message with error content
      set((state) => ({
        messages: [...state.messages, { id: crypto.randomUUID(), role: "assistant", content: `**Error:** "${errorMessage}".\n\nPlease try again or adjust your request.`, error: true }],
        error: errorMessage,
      }));

      throw err;
    } finally {
      set({ isSending: false });
    }
  },
});

export const useChat = create(chatStore);
