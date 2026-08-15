import { useEffect, useRef, useState } from "react";
import { X, Image as ImageIcon, AlertTriangle } from "lucide-react";

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
  const streamWarning = useChat((state) => state.streamWarning);
  const attachedImages = useChat((state) => state.attachedImages);
  const attachImage = useChat((state) => state.attachImage);
  const removeAttachedImage = useChat((state) => state.removeAttachedImage);

  const files = useUpload((state) => state.files);
  const clearFiles = useUpload((state) => state.clearFiles);
  const mode = useSettings((state) => state.mode);
  const uploading = files.some((file) => file.status === "processing" || file.status === "selected");

  const resize = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    if (textarea.value && textarea.value.trim().length > 0) {
      textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
    }
  };

  useEffect(() => {
    resize();
  }, [input]);

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

  const handlePaste = (e) => {
    const items = Array.from(e.clipboardData?.items || []);
    const imageItems = items.filter((item) => item.type.startsWith("image/"));

    if (imageItems.length > 0) {
      e.preventDefault();
      imageItems.slice(0, 3 - attachedImages.length).forEach((item) => {
        const file = item.getAsFile();
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
          attachImage({
            id: crypto.randomUUID(),
            name: file.name || "Pasted image",
            dataUrl: event.target?.result,
            base64: event.target?.result,
          });
        };
        reader.readAsDataURL(file);
      });
    }
  };

  const handleSend = async () => {
    if (!mode) {
      setShowModeWarning(true);
      return;
    }

    if ((!input.trim() && attachedImages.length === 0) || isSending) {
      return;
    }
    if (uploading) {
      window.addToast?.("Please wait until all documents finish uploading.", "info", 4000);
      return;
    }

    await sendMessage(input);
    clearFiles();
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
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
        {/* Uploaded Document Chips */}
        {files.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {files.map((file) => (
              <FileChip key={file.id} file={file} />
            ))}
          </div>
        )}

        {/* Inline Attached Image Preview Chips */}
        {attachedImages.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {attachedImages.map((img) => (
              <div
                key={img.id}
                className="group relative flex items-center gap-2 rounded-xl border border-border bg-background p-1.5 pr-3 shadow-sm transition hover:border-primary"
              >
                <img
                  src={img.dataUrl}
                  alt={img.name}
                  className="h-10 w-10 rounded-lg object-cover border border-border/50"
                />
                <div className="min-w-0 max-w-[130px]">
                  <p className="truncate text-xs font-medium text-text">{img.name}</p>
                  <p className="text-[10px] text-textMuted flex items-center gap-1">
                    <ImageIcon size={10} className="text-primary" /> Image context
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => removeAttachedImage(img.id)}
                  className="ml-1 rounded-full p-1 text-textMuted hover:bg-surface hover:text-text transition"
                  title="Remove image"
                >
                  <X size={13} />
                </button>
              </div>
            ))}
          </div>
        )}

        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onInput={resize}
          onChange={(event) => setInput(event.target.value)}
          onPaste={handlePaste}
          onSelect={(event) => {
            cursorRef.current = event.currentTarget.selectionStart;
            interimRangeRef.current = null;
          }}
          onKeyDown={onKeyDown}
          placeholder={
            attachedImages.length > 0
              ? "Ask a question about the attached image(s)..."
              : "Ask Sift AI anything or paste a legal clause..."
          }
          className="max-h-44 min-h-[28px] w-full resize-none bg-transparent text-text text-sm sm:text-base placeholder:text-textMuted outline-none"
        />

        {/* Structured Warning Notice from SSE */}
        {streamWarning && (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-500/10 border border-amber-500/20 p-2.5 text-xs text-text">
            <AlertTriangle size={15} className="text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-600 dark:text-amber-400">{streamWarning.message}</p>
              {streamWarning.remediation && (
                <p className="text-textMuted mt-0.5">{streamWarning.remediation}</p>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-3 rounded-xl bg-error/10 border border-error/20 p-3">
            <p className="text-sm text-error font-medium">{error}</p>
          </div>
        )}

        <ActionBar
          onSend={handleSend}
          disabled={isSending || (!input.trim() && attachedImages.length === 0)}
        />
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
