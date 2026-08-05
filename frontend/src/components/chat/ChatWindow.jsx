import { useChat } from "../../../store/chat";

import EmptyState from "./EmptyState";
import MessageList from "./MessageList";

function ChatWindow() {
  const messages = useChat((state) => state.messages);

  return (
    <section className="flex flex-1 w-full overflow-hidden">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col overflow-y-auto px-2 sm:px-4 pb-6 sm:pb-8">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <MessageList />
        )}
      </div>
    </section>
  );
}

export default ChatWindow;