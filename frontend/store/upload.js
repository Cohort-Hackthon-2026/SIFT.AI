import { create } from "zustand";
import { api } from "../src/lib/api";
import { useDocuments } from "./documents";

const uploadStore = (set, get) => ({
    files: [],
    drawerOpen: false,
    dragging: false,

    setDragging: (dragging) =>
        set({
            dragging,
        }),

    openDrawer: () =>
        set({
            drawerOpen: true,
        }),

    closeDrawer: () =>
        set({
            drawerOpen: false,
        }),

    toggleDrawer: () =>
        set((state) => ({
            drawerOpen: !state.drawerOpen,
        })),

    addFiles: (files) =>
        set((state) => {
            const created = files.map((file) => ({
                id: crypto.randomUUID(),
                name: file.name,
                size: file.size,
                type: file.type,
                status: "selected",
                pages: null,
                uploadedAt: new Date(),
                file,
            }));

            return {
                files: [...state.files, ...created],
                // return created ids to caller via synchronous return
                _lastAddedIds: created.map((c) => c.id),
            };
        }),

    updateFile: (id, updates) =>
        set((state) => ({
            files: state.files.map((file) =>
                file.id === id
                    ? {
                        ...file,
                        ...updates,
                    }
                    : file
            ),
        })),

    removeFile: (id) =>
        set((state) => ({
            files: state.files.filter(
                (file) => file.id !== id
            ),
        })),

    clearFiles: () =>
        set({
            files: [],
        }),

    uploadFile: async (id) => {
        const state = get();
        const fileObj = state.files.find((f) => f.id === id);
        if (!fileObj) return;

        // mark processing immediately
        set((s) => ({ files: s.files.map((f) => (f.id === id ? { ...f, status: "processing", progress: 0 } : f)) }));

        try {
            const form = new FormData();
            form.append("file", fileObj.file, fileObj.name);

            const resp = await api.uploadDocument(form);

            // update file as completed
            set((s) => ({ files: s.files.map((f) => (f.id === id ? { ...f, status: "completed", progress: 100, documentId: resp.document_id, pages: resp.pages?.length ?? 0 } : f)) }));

            // push into documents store
            const add = useDocuments.getState().addDocument;
            if (add && resp) add(resp);
        } catch (err) {
            set((s) => ({ files: s.files.map((f) => (f.id === id ? { ...f, status: "error", error: err.message } : f)) }));
            throw err;
        }
    },
});

export const useUpload = create(uploadStore);