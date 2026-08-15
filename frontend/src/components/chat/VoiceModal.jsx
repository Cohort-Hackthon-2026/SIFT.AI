import { LoaderCircle, Mic, Square } from "lucide-react";

function VoiceModal({ status, transcript, error, onStop, onClose }) {
  if (status === "idle") return null;

  const isListening = status === "listening";
  const isProcessing = status === "transcribing";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-overlay px-4"
      role="dialog"
      aria-modal="true"
      aria-label="Voice input"
      onClick={(e) => { if (e.target === e.currentTarget && onClose) onClose(); }}
    >
      <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-6 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <div className={`flex h-16 w-16 items-center justify-center rounded-full ${error ? "bg-error/10 text-error" : "bg-primary/10 text-primary"}`}>
            {isProcessing ? <LoaderCircle className="animate-spin" size={30} /> : <Mic size={30} />}
          </div>

          <h2 className="mt-4 text-lg font-semibold text-text">
            {isListening ? "Listening" : isProcessing ? "Transcribing" : "Voice input unavailable"}
          </h2>
          <p className="mt-2 min-h-10 text-sm text-textMuted">
            {error || transcript || (isListening ? "Speak clearly into your microphone." : "Converting your recording to text...")}
          </p>

          {isListening && (
            <button type="button" onClick={onStop} className="mt-5 flex h-11 items-center gap-2 rounded-lg bg-primary px-5 font-medium text-textInverse hover:bg-primary-hover">
              <Square size={16} fill="currentColor" />
              Finish
            </button>
          )}

          {error && (
            <button type="button" onClick={onClose} className="mt-5 h-11 rounded-lg border border-border px-5 font-medium text-text hover:bg-background">
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default VoiceModal;
