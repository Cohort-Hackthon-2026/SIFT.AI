import { create } from "zustand";
import { persist } from "zustand/middleware";

const chatStore = (set) => ({
  input: "",
  messages: [],
  isStreaming: false,

  setInput: (input) =>
    set({
      input,
    }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  clearMessages: () =>
    set({
      messages: [],
    }),

  setStreaming: (value) =>
    set({
      isStreaming: value,
    }),
});

export const useChat = create(
  persist(chatStore, {
    name: "chat",
  })
);