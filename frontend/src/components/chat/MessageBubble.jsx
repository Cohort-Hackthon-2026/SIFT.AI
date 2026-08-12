import { Bot } from "lucide-react";

import CitationBadge from "./CitationBadge";
import MarkdownRenderer from "./MarkdownRenderer";
import ChatActions from "./ChatActions";

function MessageBubble({ message }) {
    const isUser = message.role === "user";

    return (
        <>
            <div
                className={`flex gap-3 sm:gap-4 ${isUser ? "justify-end" : "justify-start"
                    }`}
            >
                {!isUser && (
                    <div className="h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary text-textInverse shadow-md hidden sm:flex">
                        <Bot size={20} />
                    </div>
                )}

                <div
                    className={`max-w-full sm:max-w-[85%] rounded-3xl border p-4 sm:p-5 transition-colors break-words ${
                        isUser
                            ? "bg-primary text-textInverse border-primary/40 shadow-md"
                            : message.error
                            ? "bg-error/10 text-text border-error/40"
                            : "bg-surface text-text border-border"
                    }`}
                >
                    {message.error ? (
                        <div className="space-y-3">
                            <div className="text-sm font-semibold text-error">Error</div>
                            <div className="text-sm text-error/90 whitespace-pre-wrap">
                                {message.content}
                            </div>
                        </div>
                    ) : (
                        <>
                            <MarkdownRenderer className={isUser ? "" : "text-justify"}>
                                {message.content}
                            </MarkdownRenderer>

                            {message.conflictAlert?.has_conflict && (
                                <div className="mt-4 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm text-text">
                                    <p className="font-semibold text-warning">
                                        {message.conflictAlert.severity || "Potential"} legal conflict
                                    </p>
                                    <p className="mt-1 text-textMuted">
                                        {message.conflictAlert.explanation || message.conflictAlert.legal_precedent}
                                    </p>
                                </div>
                            )}

                            {!isUser && (
                                <>
                                    <div className="mt-4 sm:mt-5 flex flex-wrap gap-2">
                                        {message.citations?.map((citation, index) => (
                                            <CitationBadge
                                                key={`${citation.chunk_id || citation.url || index}`}
                                                citation={citation}
                                            />
                                        ))}
                                    </div>

                                    {/* <div className="mt-5 flex gap-2">
                                        <IconButton icon={Copy} />

                                        <IconButton icon={Volume2} />
                                    </div> */}

                                </>
                            )}
                            {!isUser && <ChatActions text={message.content} />}
                        </>
                    )}
                </div>
            </div>

            {isUser && (
                <div className="flex gap-1 sm:gap-2 justify-end mt-1">
                    <ChatActions text={message.content} isCompact={true} />
                </div>
            )}
        </>
    );
}

export default MessageBubble;
