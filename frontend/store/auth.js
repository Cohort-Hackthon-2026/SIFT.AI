import { create } from "zustand";
import { persist } from "zustand/middleware";

const authStore = (set) => ({
  guest: false,
  welcomeVisible: false,
  welcomeDismissed: false,

  continueAsGuest: () => {
    try {
      let guestId = localStorage.getItem("sift_guest_session_id");
      if (!guestId) {
        guestId = `guest_${crypto.randomUUID()}`;
        localStorage.setItem("sift_guest_session_id", guestId);
      }
    } catch {}
    set({
      guest: true,
      welcomeVisible: false,
      welcomeDismissed: true,
    });
  },

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