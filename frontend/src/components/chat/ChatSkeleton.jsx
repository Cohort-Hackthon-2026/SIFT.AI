function ChatSkeleton() {
  return (
    <div className="space-y-6 py-6" role="status" aria-label="Loading chat">
      {["assistant", "user", "assistant"].map((role, index) => (
        <div key={`${role}-${index}`} className={`flex ${role === "user" ? "justify-end" : "justify-start"}`}>
          <div className={`animate-pulse rounded-3xl border border-border bg-surface p-5 ${role === "user" ? "w-[72%] sm:w-[55%]" : "w-[92%] sm:w-[78%]"}`}>
            <div className="h-3 w-1/4 rounded-full bg-border" />
            <div className="mt-4 h-3 w-full rounded-full bg-border" />
            <div className="mt-3 h-3 w-5/6 rounded-full bg-border" />
            {role === "assistant" && <div className="mt-3 h-3 w-2/3 rounded-full bg-border" />}
          </div>
        </div>
      ))}
      <span className="sr-only">Loading selected chat</span>
    </div>
  );
}

export default ChatSkeleton;
