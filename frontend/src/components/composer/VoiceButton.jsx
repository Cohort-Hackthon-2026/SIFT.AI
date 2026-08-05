import { Mic } from "lucide-react";
import IconButton from "../ui/IconButton";
import useSpeechRecognition from "../../../utils/UseSpeechRecognition";
import VoiceModal from "../chat/VoiceModal";

function VoiceButton() {
    const {
        status,
        transcript,
        error,
        start,
        stop,
        reset,
        supported,
    } = useSpeechRecognition();

    if (!supported) return null;

    return (
        <>
            <IconButton icon={Mic} onClick={start} title="Voice input" aria-label="Voice input" />
            <VoiceModal status={status} transcript={transcript} error={error} onStop={stop} onClose={reset} />
        </>
    );
}

export default VoiceButton;
