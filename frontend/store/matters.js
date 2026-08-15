import { create } from "zustand";
import { api } from "../src/lib/api";

export const useMatters = create((set) => ({
  matters: [],
  activeMatterId: null,
  loading: false,
  error: null,

  fetchMatters: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.listMatters();
      const list = Array.isArray(response) ? response : response?.matters || [];
      set({ matters: list, loading: false });
      return list;
    } catch (err) {
      set({ error: err.message, loading: false });
      return [];
    }
  },

  selectMatter: (matterId) => {
    set({ activeMatterId: matterId });
  },

  createMatter: async ({ title, client_name, practice_area = "COMMERCIAL", jurisdiction = "NG" }) => {
    set({ loading: true, error: null });
    try {
      const newMatter = await api.createMatter({
        title,
        client_name,
        practice_area,
        jurisdiction,
      });
      set((state) => ({
        matters: [newMatter, ...state.matters.filter((m) => m.matter_id !== newMatter.matter_id)],
        activeMatterId: newMatter.matter_id,
        loading: false,
      }));
      window.addToast?.(`Matter "${title}" created.`, "success");
      return newMatter;
    } catch (err) {
      set({ error: err.message, loading: false });
      window.addToast?.(`Failed to create matter: ${err.message}`, "error");
      throw err;
    }
  },

  deleteMatter: async (matterId) => {
    try {
      await api.deleteMatter(matterId);
      set((state) => ({
        matters: state.matters.filter((m) => m.matter_id !== matterId),
        activeMatterId: state.activeMatterId === matterId ? null : state.activeMatterId,
      }));
      window.addToast?.("Matter archived.", "success");
    } catch (err) {
      window.addToast?.(`Failed to delete matter: ${err.message}`, "error");
      throw err;
    }
  },
}));
