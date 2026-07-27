import { Paperclip } from "lucide-react";

import IconButton from "../ui/IconButton";
import { useUpload } from "../../../store/upload";

function UploadButton() {
    const openDrawer = useUpload(
        (state) => state.openDrawer
    );

    return (
        <IconButton
            icon={Paperclip}
            onClick={openDrawer}
            title="Upload PDF"
        />
    );
}

export default UploadButton;