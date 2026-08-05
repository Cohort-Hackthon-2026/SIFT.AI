import {
    Copy,
    Volume2,
    VolumeX,
} from "lucide-react";
import { useSpeech } from "react-text-to-speech";

import IconButton from "../ui/IconButton";

function ChatActions({ text }) {
    const { speechStatus, start, stop } = useSpeech({
        text,
        lang: "en-US",
        rate: 1,
        stableText: true,
    });
    const isSpeaking = speechStatus === "started" || speechStatus === "paused" || speechStatus === "queued";

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
