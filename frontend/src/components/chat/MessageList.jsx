import { useChat } from "../../../store/chat";

import MessageBubble from "./MessageBubble";

function MessageList() {
  const messages = useChat((state) => state.messages);
  const isSending = useChat((state) => state.isSending);
  const streamStatus = useChat((state) => state.streamStatus);
  const streamProgress = useChat((state) => state.streamProgress);

  return (
    <div className="space-y-4 sm:space-y-6 py-4 sm:py-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
        />
      ))}

      {isSending && (
        <div className="ml-0 max-w-sm sm:ml-14" aria-live="polite">
          <div className="mb-2 flex items-center justify-between gap-4 text-xs text-textMuted">
            <span>{streamStatus || "Thinking..."}</span>
            <span>{streamProgress}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-border">
            <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${streamProgress}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

export default MessageList;
