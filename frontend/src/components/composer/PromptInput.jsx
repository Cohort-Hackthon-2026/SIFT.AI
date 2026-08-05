import { useRef, useEffect, useState } from "react";

import ActionBar from "./ActionBar";
import FileChip from "./FileChip";
import Toast from "../ui/Toast";

import { useChat } from "../../../store/chat";
import { useUpload } from "../../../store/upload";
import { useSettings } from "../../../store/settings";

function PromptInput() {
  const textareaRef = useRef(null);
  const [showModeWarning, setShowModeWarning] = useState(false);

  const input = useChat((state) => state.input);
  const setInput = useChat((state) => state.setInput);
  const sendMessage = useChat((state) => state.sendMessage);
  const isSending = useChat((state) => state.isSending);
  const error = useChat((state) => state.error);

  const files = useUpload((state) => state.files);
  const mode = useSettings((state) => state.mode);

  const resize = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  };

  const handleSend = async () => {
    if (!mode) {
      setShowModeWarning(true);
      return;
    }

    if (!input.trim() || isSending) {
      return;
    }

    await sendMessage(input);
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="sticky bottom-0 mt-auto bg-gradient-to-t from-background via-background to-transparent pt-4 px-3 sm:px-0">
      <div className="mx-auto w-full max-w-4xl rounded-3xl border border-border bg-surface p-4 shadow-lg">
        {files.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {files.map((file) => (
              <FileChip key={file.id} file={file} />
            ))}
          </div>
        )}

        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onInput={resize}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask Sift AI anything..."
          className="max-h-44 min-h-[28px] w-full resize-none bg-transparent text-text text-sm sm:text-base placeholder:text-textMuted outline-none"
        />

        {error && (
          <div className="mt-3 rounded-xl bg-error/10 border border-error/20 p-3">
            <p className="text-sm text-error font-medium">{error}</p>
          </div>
        )}

        <ActionBar onSend={handleSend} disabled={isSending || !input.trim()} />
      </div>

      {showModeWarning && (
        <Toast
          message="Please select a research mode before sending a message"
          type="info"
          duration={4000}
          onClose={() => setShowModeWarning(false)}
        />
      )}
    </div>
  );
}

export default PromptInput;