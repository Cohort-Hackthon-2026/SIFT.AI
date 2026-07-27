import { Mic, MicOff } from "lucide-react";
import IconButton from "../ui/IconButton";
import useSpeechRecognition from "../../../utils/UseSpeechRecognition";

function VoiceButton() {
    const {
        listening,
        start,
        stop,
        supported,
    } = useSpeechRecognition();

    if (!supported) return null;

    return (
        <IconButton
            icon={listening ? MicOff : Mic}
            onClick={
                listening ? stop : start
            }
            className={
                listening
                    ? "bg-primary text-textInverse border-primary"
                    : ""
            }
            title="Voice Input"
        />
    );
}

export default VoiceButton;