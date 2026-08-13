import { create } from 'zustand';
import { api } from '../src/lib/api';

export const useBilling = create((set) => ({
  plan: null,
  loading: false,
  error: null,

  fetchPlan: async () => {
    set({ loading: true, error: null });
    try {
      const p = await api.getBillingPlan();
      set({ plan: p, loading: false });
      return p;
    } catch (err) {
      set({ error: err, loading: false });
      throw err;
    }
  },

  startCheckout: async (opts) => {
    set({ loading: true, error: null });
    try {
      const res = await api.startCheckout(opts);
      set({ loading: false });
      return res;
    } catch (err) {
      set({ error: err, loading: false });
      throw err;
    }
  },

  refreshPlan: async () => {
    set({ loading: true, error: null });
    try {
      const p = await api.getBillingPlan();
      set({ plan: p, loading: false });
      return p;
    } catch (err) {
      set({ error: err, loading: false });
      throw err;
    }
  },
}));
