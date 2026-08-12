import {
    Copy,
    Volume2,
    VolumeX,
} from "lucide-react";
import { useEffect, useState } from "react";

import IconButton from "../ui/IconButton";
import { useSettings } from "../../../store/settings";
import { speakText } from "../../lib/speech";

function ChatActions({ text, isCompact = false }) {
    const [isSpeaking, setIsSpeaking] = useState(false);
    const selectedVoice = useSettings((state) => state.voice);
    const voices = useSettings((state) => state.voices);
    const profile = voices.find((voice) => voice.value === selectedVoice) || voices[0];
    const stop = () => { window.speechSynthesis?.cancel(); setIsSpeaking(false); };
    const start = () => { setIsSpeaking(true); speakText(text, selectedVoice, profile, () => setIsSpeaking(false)); };
    const copyText = async () => {
        try {
            await navigator.clipboard.writeText(text);
            window.addToast?.("Copied to clipboard.", "success");
        } catch {
            window.addToast?.("Could not copy the text. Please try again.", "error", 4000);
        }
    };

    useEffect(() => () => window.speechSynthesis?.cancel(), []);

    if (isCompact) {
        return (
            <div className="flex gap-1 bg-background px-2 py-1.5 rounded-lg">
                <button
                    onClick={copyText}
                    title="Copy response"
                    aria-label="Copy response"
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-text transition-all hover:bg-surface"
                >
                    <Copy size={16} />
                </button>

                <button
                    onClick={isSpeaking ? stop : start}
                    title={isSpeaking ? "Stop reading" : "Read response aloud"}
                    aria-label={isSpeaking ? "Stop reading" : "Read response aloud"}
                    disabled={!text}
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-text transition-all hover:bg-surface disabled:opacity-50"
                >
                    {isSpeaking ? <VolumeX size={16} /> : <Volume2 size={16} />}
                </button>
            </div>
        );
    }

    return (
        <div className="mt-5 flex gap-2">

            <IconButton
                icon={Copy}
                onClick={copyText}
                title="Copy response"
                aria-label="Copy response"
            />

            <IconButton
                icon={isSpeaking ? VolumeX : Volume2}
                onClick={isSpeaking ? stop : start}
                title={isSpeaking ? "Stop reading" : "Read response aloud"}
                aria-label={isSpeaking ? "Stop reading" : "Read response aloud"}
                disabled={!text}
            />

        </div>
    );
}

export default ChatActions;
