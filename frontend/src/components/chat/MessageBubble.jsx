import {
    Bot,
    User,
    Copy,
    Volume2,
} from "lucide-react";

import CitationBadge from "./CitationBadge";
import IconButton from "../ui/IconButton";
import MarkdownRenderer from "./MarkdownRenderer";
import ChatActions from "./ChatActions";

function MessageBubble({ message }) {
    const isUser = message.role === "user";

    return (
        <div
            className={`flex gap-4 ${isUser ? "justify-end" : "justify-start"
                }`}
        >
            {!isUser && (
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-textInverse">
                    <Bot size={20} />
                </div>
            )}

            <div
                className={`max-w-[85%] rounded-3xl border border-border p-5 ${isUser
                    ? "bg-primary text-textInverse"
                    : "bg-surface text-text"
                    }`}
            >
                {/* <p className="leading-8 whitespace-pre-wrap">
                    {message.content}
                </p> */}

                <MarkdownRenderer>

                    {message.content}

                </MarkdownRenderer>

                {!isUser && (
                    <>
                        <div className="mt-5 flex flex-wrap gap-2">
                            {message.citations?.map((citation, index) => (
                                <CitationBadge
                                    key={index}
                                    citation={citation}
                                />
                            ))}
                        </div>

                        {/* <div className="mt-5 flex gap-2">
                            <IconButton icon={Copy} />

                            <IconButton icon={Volume2} />
                        </div> */}

                        <ChatActions />
                    </>
                )}
            </div>

            {isUser && (
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-textInverse">
                    <User size={20} />
                </div>
            )}
        </div>
    );
}

export default MessageBubble;