import {
    Copy,
    Volume2,
    VolumeX,
} from "lucide-react";
import { useSpeech } from "react-text-to-speech";

import IconButton from "../ui/IconButton";

function ChatActions({ text, isCompact = false }) {
    const { speechStatus, start, stop } = useSpeech({
        text,
        lang: "en-US",
        rate: 1,
        stableText: true,
    });
    const isSpeaking = speechStatus === "started" || speechStatus === "paused" || speechStatus === "queued";

    if (isCompact) {
        return (
            <div className="flex gap-1 bg-background px-2 py-1.5 rounded-lg">
                <button
                    onClick={() => navigator.clipboard.writeText(text)}
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
                onClick={() => navigator.clipboard.writeText(text)}
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
