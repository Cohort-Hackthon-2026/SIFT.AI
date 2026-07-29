import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import CodeBlock from "./CodeBlock";

function MarkdownRenderer({
    children,
}) {
    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
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
    );
}

export default MarkdownRenderer;