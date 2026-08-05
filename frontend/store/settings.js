import { create } from "zustand";
import { persist } from "zustand/middleware";

const settingsStore = (set) => ({
  mode: "",

  setMode: (mode) =>
    set({
      mode,
    }),

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
  })
);