import { create } from "zustand";
import { api } from "../src/lib/api";

const normalizeDocument = (document) => ({
  document_id: document.document_id,
  document_name: document.document_name || document.name || "Untitled document",
  source_type: document.source_type || "pdf",
  page_count: document.page_count ?? document.pages?.length ?? 0,
  chunk_count: document.chunk_count ?? document.chunks?.length ?? 0,
  file_size_bytes: document.file_size_bytes ?? 0,
  uploaded_at: document.uploaded_at,
  warnings: document.warnings || [],
});

const documentsStore = (set) => ({
  documents: [],
  drawerOpen: false,

  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),

  setDocuments: (documents) => set({ documents: documents.map(normalizeDocument) }),

  fetchDocuments: async () => {
    try {
      const docs = await api.listDocuments();
      set({ documents: (docs || []).map(normalizeDocument) });
    } catch (err) {
      console.error("fetchDocuments", err);
    }
  },

  addDocument: (doc) =>
    set((state) => ({ documents: [normalizeDocument(doc), ...(state.documents || [])] })),

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
