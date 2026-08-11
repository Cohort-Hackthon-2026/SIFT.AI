import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import CodeBlock from "./CodeBlock";

function MarkdownRenderer({
    children,
    className = "",
}) {
    return (
        <div className={className}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    p({ children }) {
                        return <p className="mt-4 first:mt-0 leading-7">{children}</p>;
                    },
                    code({
                        inline,
                        className,
                        children,
                    }) {
                        const match =
                            /language-(\w+)/.exec(
                                className || ""
                            );

                        if (!inline && match) {
                            return (
                                <CodeBlock
                                    language={match[1]}
                                    value={String(children)}
                                />
                            );
                        }

                        return (
                            <code className="rounded bg-background px-1 py-0.5 text-primary">
                                {children}
                            </code>
                        );
                    },
                }}
            >
                {children}
            </ReactMarkdown>
        </div>
    );
}

export default MarkdownRenderer;