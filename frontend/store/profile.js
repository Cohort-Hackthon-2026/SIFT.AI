import { create } from 'zustand';
import { api } from '../src/lib/api';

export const useProfile = create((set, get) => ({
  profile: null,
  loading: false,
  error: null,

  fetchProfile: async () => {
    set({ loading: true, error: null });
    try {
      const p = await api.getMyProfile();
      set({ profile: p, loading: false });
      return p;
    } catch (err) {
      set({ error: err, loading: false });
      throw err;
    }
  },

  updateProfile: async (patch) => {
    set({ loading: true, error: null });
    try {
      const p = await api.updateMyProfile(patch);
      set({ profile: p, loading: false });
      return p;
    } catch (err) {
      set({ error: err, loading: false });
      throw err;
    }
  },

  hasRole: () => {
    const state = useProfile.getState();
    return state.profile?.role && state.profile.role !== null && state.profile.role !== '';
  },
}));

