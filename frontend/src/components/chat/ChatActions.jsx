import {
    Copy,
    Volume2,
    VolumeX,
    FileDown,
} from "lucide-react";
import { useEffect, useState } from "react";

import IconButton from "../ui/IconButton";
import ExportModal from "./ExportModal";
import { useSettings } from "../../../store/settings";
import { useChat } from "../../../store/chat";
import { speakText } from "../../lib/speech";

function ChatActions({ text, isCompact = false }) {
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [exportOpen, setExportOpen] = useState(false);

    const activeChatId = useChat((state) => state.activeChatId);
    const chats = useChat((state) => state.chats);
    const currentChat = chats.find((c) => c.chat_id === activeChatId);

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
                    title="Copy prompt"
                    aria-label="Copy prompt"
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-text transition-all hover:bg-surface"
                >
                    <Copy size={16} />
                </button>
            </div>
        );
    }

    return (
        <>
            <div className="mt-5 flex items-center gap-2">
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

                {activeChatId && (
                    <IconButton
                        icon={FileDown}
                        onClick={() => setExportOpen(true)}
                        title="Export Research Memo (PDF / Word / PPTX)"
                        aria-label="Export Research Memo"
                    />
                )}
            </div>

            <ExportModal
                isOpen={exportOpen}
                onClose={() => setExportOpen(false)}
                chatId={activeChatId}
                chatTitle={currentChat?.title || "Legal_Research_Memo"}
            />
        </>
    );
}

export default ChatActions;
