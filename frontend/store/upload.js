import { create } from "zustand";

const uploadStore = (set) => ({
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
        set((state) => ({
            files: [
                ...state.files,
                ...files.map((file) => ({
                    id: crypto.randomUUID(),
                    name: file.name,
                    size: file.size,
                    type: file.type,
                    status: "selected",
                    pages: null,
                    uploadedAt: new Date(),
                    file,
                })),
            ],
        })),

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
});

export const useUpload = create(uploadStore);