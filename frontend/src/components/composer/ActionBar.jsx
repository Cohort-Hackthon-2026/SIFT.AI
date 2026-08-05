import UploadButton from "./UploadButton";
import VoiceButton from "./VoiceButton";
import SendButton from "./SendButton";
// import ModeSwitcher from "./ModeSwitcher";

function ActionBar({ onSend, disabled = false }) {
    return (
        <div className="mt-3 sm:mt-4 flex flex-wrap items-center justify-between gap-2 sm:gap-3">
            <div className="flex items-center gap-1.5 sm:gap-2">
                <UploadButton />
                <VoiceButton />
            </div>

            {/* <ModeSwitcher /> */}

            <SendButton onClick={onSend} disabled={disabled} />
        </div>
    );
}

export default ActionBar;