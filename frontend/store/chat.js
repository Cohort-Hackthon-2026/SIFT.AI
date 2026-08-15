import { create } from "zustand";

import { api } from "../src/lib/api";
import { streamChatQuery } from "../src/lib/sseClient";
import { generateChatTitle } from "../src/lib/titleGenerator";
import { useDocuments } from "./documents";
import { useSettings } from "./settings";

const normalizeCitation = (citation) => {
  if (!citation) {
    return null;
  }

  const rawDocId = String(citation.document_id || "");
  const rawDocName = citation.document_name || citation.document || "";
  const isChatText =
    citation.source === "chat_text" ||
    citation.source === "text" ||
    citation.source === "user_text" ||
    rawDocId.startsWith("chat-text-") ||
    rawDocName === "Chat Context" ||
    rawDocName === "User Statement Context";

  const rawTextContent =
    citation.text ||
    citation.content ||
    citation.excerpt ||
    citation.statement ||
    (typeof citation.chunk_id === "string" && !citation.chunk_id.includes("-") ? citation.chunk_id : "") ||
    "";

  if (isChatText) {
    return {
      label: "User Text Statement",
      document: rawDocName === "Chat Context" ? "User Statement & Incident Context" : (rawDocName || "User Statement"),
      page: null,
      content: rawTextContent,
      text: rawTextContent,
      statement: citation.statement || citation.exact_statement || "",
      bounding_boxes: [],
      file_url: null,
      source: "chat_text",
      ...citation,
      source: "chat_text",
    };
  }

  if (citation.document_id) {
    const isImage = citation.source === "image";
    return {
      label: `${rawDocName || "Document"} · p${citation.page_number || 1}`,
      document: rawDocName || "Document",
      page: citation.page_number || 1,
      content: rawTextContent,
      text: rawTextContent,
      bounding_boxes: citation.bounding_boxes || [],
      file_url: citation.file_url || null,
      source: citation.source || (isImage ? "image" : "pdf"),
      ...citation,
    };
  }

  if (citation.title || citation.url) {
    return {
      label: citation.title || "Web Authority",
      document: citation.domain || "Web source",
      page: null,
      content: rawTextContent || citation.url || "",
      text: rawTextContent,
      source: "web",
      ...citation,
    };
  }

  return {
    label: citation.label || "Citation",
    document: citation.document || "Legal Reference",
    content: rawTextContent,
    text: rawTextContent,
    source: citation.source || "chat_text",
    ...citation,
  };
};

const normalizeMessage = (message) => ({
  id: message.message_id || message.id || crypto.randomUUID(),
  role: message.role,
  content: message.content || "",
  images: message.metadata?.images || [],
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
  attachedImages: [], // Array of { id, dataUrl, base64, name }
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
  streamWarning: null,
  error: null,

  setInput: (input) => set((state) => ({ input: typeof input === "function" ? input(state.input) : input })),

  attachImage: (imageObj) =>
    set((state) => {
      if (state.attachedImages.length >= 3) {
        window.addToast?.("Maximum 3 images allowed per message", "info");
        return state;
      }
      return { attachedImages: [...state.attachedImages, imageObj] };
    }),

  removeAttachedImage: (id) =>
    set((state) => ({
      attachedImages: state.attachedImages.filter((img) => img.id !== id),
    })),

  clearAttachedImages: () => set({ attachedImages: [] }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  clearMessages: () => set({ messages: [] }),

  setStreaming: (value) => set({ isSending: value }),

  setActiveChatId: (activeChatId) => set({ activeChatId }),

  setChats: (chats) => set({ chats }),

  setMessages: (messages) => set({ messages }),

  createNewChat: async (title = "New Research Thread") => {
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

  renameChat: async (chatId, title) => {
    const trimmed = (title || "").trim();
    if (!trimmed || !chatId) return;

    // Optimistic local update
    set((state) => ({
      chats: state.chats.map((c) => (c.chat_id === chatId ? { ...c, title: trimmed } : c)),
    }));

    try {
      await api.updateChat(chatId, { title: trimmed });
    } catch (err) {
      console.warn("Failed to persist renamed chat title:", err);
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

  sendMessage: async (content, customImages = null) => {
    const trimmed = content?.trim();
    const imagesToAttach = customImages !== null ? customImages : get().attachedImages;

    if (!trimmed && imagesToAttach.length === 0) {
      return null;
    }

    const documentIds = (useDocuments.getState().documents || []).map((doc) => doc.document_id);
    let chatId = get().activeChatId;

    if (!chatId) {
      const generatedTitle = generateChatTitle(trimmed, imagesToAttach.length > 0 ? "Document & Image Analysis" : "Legal Research");
      const createdChat = await get().createNewChat(generatedTitle);
      chatId = createdChat.chat_id;
    } else {
      // If the current chat has a generic/placeholder title, update it dynamically from the query
      const currentChat = get().chats.find((c) => c.chat_id === chatId);
      const isGenericTitle =
        !currentChat?.title ||
        currentChat.title === "New Research Chat" ||
        currentChat.title === "New Research Thread" ||
        currentChat.title === "New research chat" ||
        currentChat.title === "Untitled" ||
        currentChat.title === "New Chat";

      if (isGenericTitle && trimmed) {
        const smartTitle = generateChatTitle(trimmed, "Legal Research");
        void get().renameChat(chatId, smartTitle);
      }
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed || "Please analyse the attached image(s).",
      images: imagesToAttach.map((img) => img.dataUrl || img.base64),
    };
    const assistantMessage = { id: crypto.randomUUID(), role: "assistant", content: "", citations: [] };
    let assistantMetadata = {};

    set((state) => ({
      messages: [...state.messages, userMessage],
      input: "",
      attachedImages: [],
      isSending: true,
      error: null,
      streamStatus: "",
      streamProgress: 0,
      streamSteps: [],
      streamWarning: null,
    }));

    try {
      const mode = useSettings.getState().mode;
      let assistantContent = "";
      let citations = [];

      // Extract raw base64 string without data:image/...;base64, prefix if present
      const base64Images = imagesToAttach.map((img) => {
        const raw = img.base64 || img.dataUrl || "";
        return raw.includes(",") ? raw.split(",")[1] : raw;
      }).filter(Boolean);

      await streamChatQuery({
        payload: {
          query: trimmed || "Please analyse the attached image(s).",
          chat_id: chatId,
          mode: (mode || "STRICT").toUpperCase(),
          document_ids: documentIds,
          images: base64Images.length > 0 ? base64Images : undefined,
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
          assistantMetadata = {
            conflictAlert: payload.conflict_alert || null,
            mode: payload.mode,
          };
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
        onModeChange: (data) => {
          if (data?.to) {
            useSettings.getState().setMode(data.to.toLowerCase());
            window.addToast?.(`Session mode updated to ${data.to}`, "info");
          }
        },
        onError: (errPayload) => {
          if (errPayload?.message) {
            set({
              streamWarning: {
                code: errPayload.code,
                message: errPayload.message,
                remediation: errPayload.remediation,
              },
            });
            window.addToast?.(errPayload.message, "warning", 5000);
          }
        },
      });

      const completedAssistantMessage = {
        ...assistantMessage,
        content: assistantContent,
        citations,
        ...assistantMetadata,
      };
      set((state) => ({ messages: [...state.messages, completedAssistantMessage] }));

      if (!get().chats.some((chat) => chat.chat_id === chatId)) {
        await get().loadChats();
      }

      return completedAssistantMessage;
    } catch (err) {
      let errorMessage = err.message || "An error occurred";
      if (err.detail) {
        if (typeof err.detail === "string") {
          errorMessage = err.detail;
        } else if (Array.isArray(err.detail)) {
          errorMessage = err.detail.map((e) => e.msg || e.message || JSON.stringify(e)).join("; ");
        }
      }

      set((state) => ({
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `**Error:** "${errorMessage}".\n\nPlease try again or adjust your request.`,
            error: true,
          },
        ],
        error: errorMessage,
      }));

      throw err;
    } finally {
      set({ isSending: false });
    }
  },
});

export const useChat = create(chatStore);
