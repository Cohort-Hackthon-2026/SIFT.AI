import { useChat } from "../../../store/chat";

import MessageBubble from "./MessageBubble";
import { Check, LoaderCircle } from "lucide-react";

function MessageList() {
  const messages = useChat((state) => state.messages);
  const isSending = useChat((state) => state.isSending);
  const streamStatus = useChat((state) => state.streamStatus);
  const streamProgress = useChat((state) => state.streamProgress);
  const streamSteps = useChat((state) => state.streamSteps);

  return (
    <div className="space-y-4 sm:space-y-6 py-4 sm:py-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
        />
      ))}

      {isSending && (
        <div className="ml-0 max-w-md rounded-lg border border-border bg-surface p-4 sm:ml-14" aria-live="polite">
          <div className="mb-2 flex items-center justify-between gap-4 text-xs text-textMuted">
            <span>{streamStatus || "Waiting for the server..."}</span>
            <span>{streamProgress}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-border">
            <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${streamProgress}%` }} />
          </div>

          {streamSteps.length > 0 && (
            <ol className="mt-4 space-y-2">
              {streamSteps.map((item, index) => {
                const isCurrent = index === streamSteps.length - 1 && item.progress < 100;
                return (
                  <li key={item.step} className="flex items-start gap-2 text-sm text-textMuted">
                    {isCurrent ? (
                      <LoaderCircle className="mt-0.5 shrink-0 animate-spin text-primary" size={16} />
                    ) : (
                      <Check className="mt-0.5 shrink-0 text-success" size={16} />
                    )}
                    <span>{item.step}</span>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

export default MessageList;
