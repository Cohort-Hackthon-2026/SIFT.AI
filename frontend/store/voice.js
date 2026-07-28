import { create } from "zustand";

const voiceStore = (set) => ({
    open: false,
    listening: false,
    transcript: "",

    setTranscript: (transcript) =>
        set({
            transcript,
        }),

    openModal: () =>
        set({
            open: true,
        }),

    closeModal: () =>
        set({
            open: false,
            listening: false,
            transcript: "",
        }),

    setListening: (listening) =>
        set({
            listening,
        }),
});

export const useVoice = create(voiceStore);