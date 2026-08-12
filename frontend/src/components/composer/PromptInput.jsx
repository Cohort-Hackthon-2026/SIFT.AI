import { useEffect, useRef, useState } from "react";

import ActionBar from "./ActionBar";
import FileChip from "./FileChip";
import Toast from "../ui/Toast";

import { useChat } from "../../../store/chat";
import { useUpload } from "../../../store/upload";
import { useSettings } from "../../../store/settings";

function PromptInput() {
  const composerRef = useRef(null);
  const textareaRef = useRef(null);
  const cursorRef = useRef(0);
  const interimRangeRef = useRef(null);
  const [showModeWarning, setShowModeWarning] = useState(false);

  const input = useChat((state) => state.input);
  const setInput = useChat((state) => state.setInput);
  const sendMessage = useChat((state) => state.sendMessage);
  const isSending = useChat((state) => state.isSending);
  const error = useChat((state) => state.error);

  const files = useUpload((state) => state.files);
  const clearFiles = useUpload((state) => state.clearFiles);
  const mode = useSettings((state) => state.mode);
  const uploading = files.some((file) => file.status === "processing" || file.status === "selected");

  const resize = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  };

  useEffect(() => {
    const insertTranscript = (event) => {
      const text = event.detail?.text || "";
      const current = useChat.getState().input;
      const range = event.detail?.replaceInterim && interimRangeRef.current
        ? interimRangeRef.current
        : { start: cursorRef.current, end: cursorRef.current };
      const next = `${current.slice(0, range.start)}${text}${current.slice(range.end)}`;
      setInput(next);
      const end = range.start + text.length;
      cursorRef.current = end;
      interimRangeRef.current = event.detail?.replaceInterim ? { start: range.start, end } : null;
      requestAnimationFrame(() => textareaRef.current?.setSelectionRange(end, end));
    };
    window.addEventListener("voice-transcript", insertTranscript);
    return () => window.removeEventListener("voice-transcript", insertTranscript);
  }, [setInput]);

  useEffect(() => {
    const composer = composerRef.current;
    if (!composer) return undefined;

    const updateComposerHeight = () => {
      document.documentElement.style.setProperty("--composer-height", `${composer.offsetHeight}px`);
    };
    const observer = new ResizeObserver(updateComposerHeight);
    observer.observe(composer);
    updateComposerHeight();

    return () => {
      observer.disconnect();
      document.documentElement.style.removeProperty("--composer-height");
    };
  }, []);

  const handleSend = async () => {
    if (!mode) {
      setShowModeWarning(true);
      return;
    }

    if (!input.trim() || isSending) {
      return;
    }
    if (uploading) {
      window.addToast?.("Please wait until all documents finish uploading.", "info", 4000);
      return;
    }

    await sendMessage(input);
    clearFiles();
  };

  const onKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  };

  return (
    <div ref={composerRef} className="sticky bottom-0 mt-auto bg-gradient-to-t from-background via-background to-transparent pt-4 px-3 sm:px-0">
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
          onSelect={(event) => { cursorRef.current = event.currentTarget.selectionStart; interimRangeRef.current = null; }}
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
