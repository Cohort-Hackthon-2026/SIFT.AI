import { create } from "zustand";
import { persist } from "zustand/middleware";

const themeStore = (set) => ({
  theme: "light",

  setTheme: (theme) => set({ theme }),

  toggleTheme: () =>
    set((state) => ({
      theme: state.theme === "light" ? "dark" : "light",
    })),
});

export const useTheme = create(
  persist(themeStore, {
    name: "theme",
  })
);