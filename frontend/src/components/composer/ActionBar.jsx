import { useRef } from "react";
import { ImagePlus } from "lucide-react";
import UploadButton from "./UploadButton";
import VoiceButton from "./VoiceButton";
import SendButton from "./SendButton";
import { useChat } from "../../../store/chat";

function ActionBar({ onSend, disabled = false }) {
  const fileInputRef = useRef(null);
  const attachImage = useChat((state) => state.attachImage);
  const attachedImages = useChat((state) => state.attachedImages);

  const handleImageSelect = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    files.slice(0, 3 - attachedImages.length).forEach((file) => {
      if (!file.type.startsWith("image/")) {
        window.addToast?.("Please select image files only (PNG, JPG, WebP)", "error");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        window.addToast?.(`Image "${file.name}" exceeds the 5MB size limit`, "warning");
        return;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        attachImage({
          id: crypto.randomUUID(),
          name: file.name,
          dataUrl: event.target?.result,
          base64: event.target?.result,
        });
      };
      reader.readAsDataURL(file);
    });

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="mt-3 sm:mt-4 flex flex-wrap items-center justify-between gap-2 sm:gap-3">
      <div className="flex items-center gap-1.5 sm:gap-2">
        <UploadButton />
        <VoiceButton />

        {/* Inline Image Attachment Button */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/tiff"
          multiple
          className="hidden"
          onChange={handleImageSelect}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          title="Attach image of contract/evidence"
          aria-label="Attach image"
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-background text-text transition-all duration-200 hover:border-primary hover:bg-primary/10 hover:text-primary active:scale-95"
        >
          <ImagePlus size={18} />
        </button>
      </div>

      <SendButton onClick={onSend} disabled={disabled} />
    </div>
  );
}

export default ActionBar;