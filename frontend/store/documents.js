import { create } from "zustand";
import { api } from "../src/lib/api";

const documentsStore = (set) => ({
  documents: [],
  drawerOpen: false,

  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),

  setDocuments: (documents) => set({ documents }),

  fetchDocuments: async () => {
    try {
      const docs = await api.listDocuments();
      set({ documents: docs });
    } catch (err) {
      console.error("fetchDocuments", err);
    }
  },

  addDocument: (doc) =>
    set((state) => ({ documents: [doc, ...(state.documents || [])] })),

  removeDocumentLocal: (documentId) =>
    set((state) => ({ documents: state.documents.filter((d) => d.document_id !== documentId) })),

  deleteDocument: async (documentId) => {
    try {
      await api.deleteDocument(documentId);
      set((state) => ({ documents: state.documents.filter((d) => d.document_id !== documentId) }));
    } catch (err) {
      if (err.status === 404) {
        // treat as success
        set((state) => ({ documents: state.documents.filter((d) => d.document_id !== documentId) }));
      } else {
        console.error("deleteDocument", err);
        throw err;
      }
    }
  },
});

export const useDocuments = create(documentsStore);
