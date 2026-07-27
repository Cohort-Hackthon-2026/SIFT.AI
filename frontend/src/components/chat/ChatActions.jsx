import {
    Copy,
    Volume2,
    RotateCcw,
} from "lucide-react";

import IconButton from "../ui/IconButton";

function ChatActions() {
    return (
        <div className="mt-5 flex gap-2">

            <IconButton
                icon={Copy}
            />

            <IconButton
                icon={Volume2}
            />

            <IconButton
                icon={RotateCcw}
            />

        </div>
    );
}

export default ChatActions;