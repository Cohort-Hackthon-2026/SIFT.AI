import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

function CodeBlock({
    language,
    value,
}) {
    return (
        <SyntaxHighlighter
            language={language}
            style={oneDark}
            customStyle={{
                borderRadius: 16,
                fontSize: 14,
            }}
        >
            {value}
        </SyntaxHighlighter>
    );
}

export default CodeBlock;