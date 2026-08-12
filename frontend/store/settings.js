import { create } from "zustand";
import { persist } from "zustand/middleware";

const settingsStore = (set) => ({
  mode: "",
  voice: "default",
  voices: [
    { value: "default", label: "Balanced", description: "Clear and natural for everyday reading.", pitch: 1, rate: 1 },
    { value: "calm", label: "Calm", description: "A softer, relaxed delivery.", pitch: 0.9, rate: 0.9 },
    { value: "bright", label: "Bright", description: "Warm, upbeat and engaging.", pitch: 1.15, rate: 1.05 },
    { value: "deep", label: "Deep", description: "A lower, confident tone.", pitch: 0.72, rate: 0.95 },
    { value: "clear", label: "Clear", description: "Crisp and precise for research.", pitch: 1.05, rate: 0.95 },
    { value: "quick", label: "Quick", description: "A faster voice for shorter reviews.", pitch: 1, rate: 1.2 },
  ],

  setMode: (mode) =>
    set({
      mode,
    }),
  setVoice: (voice) => set({ voice }),

  modes: [
    {
      value: "strict",
      label: "Strict",
      description: "Answers only from uploaded documents.",
    },
    {
      value: "enhanced",
      label: "Enhanced",
      description:
        "Combines your documents with trusted web sources.",
    },
  ],
});

export const useSettings = create(
  persist(settingsStore, {
    name: "settings",
    version: 1,
    partialize: (state) => ({
      mode: state.mode,
      voice: state.voice,
    }),
    merge: (persistedState, currentState) => {
      const saved = persistedState || {};
      const validVoice = currentState.voices.some((voice) => voice.value === saved.voice)
        ? saved.voice
        : "default";

      return {
        ...currentState,
        mode: saved.mode || currentState.mode,
        voice: validVoice,
      };
    },
  })
);
