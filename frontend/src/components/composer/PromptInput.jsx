import { useRef } from "react";

import ActionBar from "./ActionBar";
import FileChip from "./FileChip";

import { useChat } from "../../../store/chat";
import { useUpload } from "../../../store/upload";

function PromptInput() {
  const textareaRef = useRef(null);

  const input = useChat((state) => state.input);
  const setInput = useChat((state) => state.setInput);

  const files = useUpload((state) => state.files);

  const resize = () => {
    const textarea = textareaRef.current;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(
      textarea.scrollHeight,
      180
    )}px`;
  };

  return (
    <div className="sticky bottom-0 mt-auto bg-background pt-4">
      <div className="mx-auto w-full max-w-4xl rounded-3xl border border-border bg-surface p-4 shadow-sm">

        {files.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {files.map((file) => (
              <FileChip
                key={file.id}
                file={file}
              />
            ))}
          </div>
        )}

        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onInput={resize}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Sift AI anything..."
          className="max-h-44 min-h-[28px] w-full resize-none bg-transparent text-text placeholder:text-textMuted outline-none"
        />

        <ActionBar />

      </div>
    </div>
  );
}

export default PromptInput;