import { create } from 'zustand';

export const useUI = create((set) => ({
  upgradeModalOpen: false,
  upgradeModalDetail: null,
  openUpgradeModal: (detail) => set({ upgradeModalOpen: true, upgradeModalDetail: detail }),
  closeUpgradeModal: () => set({ upgradeModalOpen: false, upgradeModalDetail: null }),

  roleSelectionModalOpen: false,
  openRoleSelectionModal: () => set({ roleSelectionModalOpen: true }),
  closeRoleSelectionModal: () => set({ roleSelectionModalOpen: false }),

  chamberSelectionModalOpen: false,
  openChamberSelectionModal: () => set({ chamberSelectionModalOpen: true }),
  closeChamberSelectionModal: () => set({ chamberSelectionModalOpen: false }),

  billingModalOpen: false,
  openBillingModal: () => set({ billingModalOpen: true }),
  closeBillingModal: () => set({ billingModalOpen: false }),
}));
