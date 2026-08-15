import { create } from 'zustand';
import { api } from '../src/lib/api';

export const useBilling = create((set, get) => ({
  plan: null,
  loading: false,
  error: null,
  processingPayment: false,
  lastCheckoutTier: null,

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
    set({ loading: true, error: null, lastCheckoutTier: opts.tier });
    try {
      const res = await api.startCheckout(opts);
      // Set processingPayment for both Paystack and mock mode
      // Paystack will redirect, mock will poll for webhook completion
      set({ processingPayment: true, loading: false });
      return res;
    } catch (err) {
      set({ error: err, loading: false, processingPayment: false, lastCheckoutTier: null });
      throw err;
    }
  },

  refreshPlan: async () => {
    try {
      const p = await api.getBillingPlan();
      const prevTier = get().plan?.tier;
      const newTier = p?.tier;
      const targetTier = get().lastCheckoutTier;

      // If tier changed and it's the target tier, payment succeeded
      if (prevTier && newTier && prevTier !== newTier && newTier === targetTier) {
        set({ 
          plan: p, 
          processingPayment: false, 
          lastCheckoutTier: null,
          loading: false 
        });
        return { success: true, tier: newTier };
      } else if (prevTier && newTier && prevTier !== newTier) {
        // Tier changed but not to target (unexpected)
        set({ plan: p, processingPayment: false, lastCheckoutTier: null, loading: false });
        return { success: true, tier: newTier };
      }

      set({ plan: p });
      return { success: false, tier: newTier };
    } catch (err) {
      set({ error: err });
      return { success: false, error: err };
    }
  },

  verifyPayment: async (reference, targetTier = null) => {
    set({ loading: true, error: null });
    try {
      const tier = targetTier || get().lastCheckoutTier;
      const res = await api.verifyPayment(reference, tier);
      const p = await api.getBillingPlan();
      set({
        plan: p,
        processingPayment: false,
        lastCheckoutTier: null,
        loading: false,
      });
      return { success: true, tier: res?.tier || p?.tier, data: res };
    } catch (err) {
      set({ error: err, loading: false, processingPayment: false });
      throw err;
    }
  },

  resetPaymentState: () => {
    set({ processingPayment: false, lastCheckoutTier: null, error: null });
  },
}));

