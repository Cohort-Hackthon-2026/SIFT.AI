import UploadButton from "./UploadButton";
import VoiceButton from "./VoiceButton";
import SendButton from "./SendButton";
// import ModeSwitcher from "./ModeSwitcher";

function ActionBar() {
    return (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">

            <div className="flex items-center gap-2">
                <UploadButton />

                <VoiceButton />
            </div>

            {/* <ModeSwitcher /> */}

            <SendButton />

        </div>
    );
}

export default ActionBar;