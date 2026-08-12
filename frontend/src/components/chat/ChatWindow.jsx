import { useEffect, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";

import { useChat } from "../../../store/chat";

import EmptyState from "./EmptyState";
import MessageList from "./MessageList";
import ChatSkeleton from "./ChatSkeleton";

function ChatWindow() {
  const scrollRef = useRef(null);
  const contentRef = useRef(null);
  const endRef = useRef(null);
  const shouldFollowRef = useRef(true);
  const [showLatestButton, setShowLatestButton] = useState(false);
  const messages = useChat((state) => state.messages);
  const isLoadingMessages = useChat((state) => state.isLoadingMessages);
  const activeChatId = useChat((state) => state.activeChatId);
  const chatLoadVersion = useChat((state) => state.chatLoadVersion);

  const scrollToLatest = (behavior = "smooth") => {
    const container = scrollRef.current;
    const end = endRef.current;
    if (!container && !end) return;

    shouldFollowRef.current = true;
    setShowLatestButton(false);
    end?.scrollIntoView({ behavior, block: "end" });
  };

  useEffect(() => {
    const content = contentRef.current;
    if (!content) return undefined;

    const observer = new ResizeObserver(() => {
      if (shouldFollowRef.current && !isLoadingMessages) {
        scrollToLatest("smooth");
      }
    });
    observer.observe(content);
    return () => observer.disconnect();
  }, [isLoadingMessages]);

  useEffect(() => {
    const end = endRef.current;
    if (!end || isLoadingMessages || messages.length === 0) {
      setShowLatestButton(false);
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        const isAtLatest = entry.isIntersecting;
        shouldFollowRef.current = isAtLatest;
        setShowLatestButton(!isAtLatest);
      },
      { threshold: 0.01 },
    );
    observer.observe(end);
    return () => observer.disconnect();
  }, [isLoadingMessages, messages.length]);

  useEffect(() => {
    if (!chatLoadVersion || isLoadingMessages || !activeChatId) return undefined;

    shouldFollowRef.current = true;
    const frame = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [activeChatId, chatLoadVersion, isLoadingMessages]);

  return (
    <section className="relative flex flex-1 w-full min-h-0 overflow-hidden">
      <div ref={scrollRef} className="mx-auto flex w-full max-w-4xl flex-1 flex-col overflow-y-auto scroll-smooth px-2 sm:px-4 pb-6 sm:pb-8">
        <div ref={contentRef}>
          {isLoadingMessages ? (
            <ChatSkeleton />
          ) : messages.length === 0 ? (
            <EmptyState />
          ) : (
            <MessageList />
          )}
          <div ref={endRef} className="h-px w-full" aria-hidden="true" />
        </div>
      </div>

      {showLatestButton && (
        <button
          type="button"
          onClick={() => scrollToLatest("smooth")}
          className="fixed right-4 z-20 flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface text-text shadow-lg transition hover:border-primary hover:text-primary sm:right-6 lg:right-8"
          style={{ bottom: "calc(var(--composer-height, 112px) + 16px)" }}
          aria-label="Scroll to latest response"
          title="Scroll to latest response"
        >
          <ArrowDown size={20} />
        </button>
      )}
    </section>
  );
}

export default ChatWindow;
