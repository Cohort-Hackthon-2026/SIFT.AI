import { create } from "zustand";
import { persist } from "zustand/middleware";

const authStore = (set) => ({
  guest: false,
  welcomeVisible: false,
  welcomeDismissed: false,

  continueAsGuest: () =>
    set({
      guest: true,
      welcomeVisible: false,
      welcomeDismissed: true,
    }),

  resetGuest: () =>
    set({
      guest: false,
    }),

  openWelcome: () =>
    set({
      welcomeVisible: true,
      welcomeDismissed: false,
    }),

  closeWelcome: () =>
    set({
      welcomeVisible: false,
      welcomeDismissed: true,
    }),
});

export const useAuth = create(
  persist(authStore, {
    name: "sift-auth",
    partialize: (state) => ({
      guest: state.guest,
    }),
  })
);