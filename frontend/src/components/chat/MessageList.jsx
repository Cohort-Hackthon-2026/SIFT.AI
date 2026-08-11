import { useChat } from "../../../store/chat";

import MessageBubble from "./MessageBubble";

function MessageList() {
  const messages = useChat((state) => state.messages);
  const isSending = useChat((state) => state.isSending);

  return (
    <div className="space-y-4 sm:space-y-6 py-4 sm:py-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
        />
      ))}

      {isSending && (
        <div className="ml-0 flex w-fit items-center gap-1 rounded-2xl border border-border bg-surface px-4 py-3 shadow-sm sm:ml-14" aria-label="AI is working" aria-live="polite">
          {[0, 1, 2].map((index) => <span key={index} className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: `${index * 140}ms` }} />)}
        </div>
      )}
    </div>
  );
}

export default MessageList;
