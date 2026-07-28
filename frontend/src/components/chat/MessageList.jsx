import { useChat } from "../../../store/chat";

import MessageBubble from "./MessageBubble";

function MessageList() {
  const messages = useChat((state) => state.messages);

  return (
    <div className="space-y-8 py-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
        />
      ))}
    </div>
  );
}

export default MessageList;