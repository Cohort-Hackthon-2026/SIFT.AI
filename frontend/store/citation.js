import { create } from "zustand";

const citationStore = (set) => ({
    open: false,
    citation: null,

    openCitation: (citation) =>
        set({
            open: true,
            citation,
        }),

    closeCitation: () =>
        set({
            open: false,
            citation: null,
        }),
});

export const useCitation = create(citationStore);