import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FileText, ExternalLink, Scale } from "lucide-react";
import CodeBlock from "./CodeBlock";
import { useCitation } from "../../../store/citation";

function transformInlineCitations(text) {
  if (typeof text !== "string") return text;

  // 1. Transform [Doc: filename, Page: X] -> [#citation-doc-filename-X]
  let transformed = text.replace(
    /\[(?:Doc|Document):\s*([^,\]]+?),\s*Page:\s*(\d+)\]/gi,
    (match, docName, pageNum) => {
      const cleanDoc = docName.trim();
      const cleanPage = pageNum.trim();
      const safeHref = `#citation-doc-${encodeURIComponent(cleanDoc)}-${cleanPage}`;
      return `[${cleanDoc} (p.${cleanPage})](${safeHref})`;
    }
  );

  // 2. Transform [Doc: filename] (without page) -> [#citation-doc-filename-1]
  transformed = transformed.replace(
    /\[(?:Doc|Document):\s*([^,\]]+?)\]/gi,
    (match, docName) => {
      const cleanDoc = docName.trim();
      const safeHref = `#citation-doc-${encodeURIComponent(cleanDoc)}-1`;
      return `[${cleanDoc}](${safeHref})`;
    }
  );

  // 3. Transform Nigerian Court badges [SC], [CA], [FHC], [NIC]
  transformed = transformed.replace(
    /\[(SC|CA|FHC|NIC|SHCL|SHCA)\](?!\()/g,
    (match, courtCode) => {
      const names = {
        SC: "Supreme Court",
        CA: "Court of Appeal",
        FHC: "Federal High Court",
        NIC: "National Industrial Court",
        SHCL: "State High Court (Lagos)",
        SHCA: "State High Court (Abuja)",
      };
      return `[${names[courtCode] || courtCode} (${courtCode})](#court-${courtCode.toLowerCase()})`;
    }
  );

  return transformed;
}

function MarkdownRenderer({ children, className = "" }) {
  const processedContent = useMemo(() => {
    return transformInlineCitations(children);
  }, [children]);

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p({ children }) {
            return <p className="mt-4 first:mt-0 leading-7">{children}</p>;
          },
          a({ href, children }) {
            if (href?.startsWith("#citation-doc-")) {
              const raw = href.replace("#citation-doc-", "");
              const lastDash = raw.lastIndexOf("-");
              let docName = raw;
              let page = "1";
              if (lastDash !== -1) {
                docName = decodeURIComponent(raw.slice(0, lastDash));
                page = raw.slice(lastDash + 1);
              } else {
                docName = decodeURIComponent(raw);
              }

              return (
                <button
                  type="button"
                  onClick={() => {
                    useCitation.getState().openCitation({
                      document: docName,
                      title: docName,
                      page: parseInt(page, 10) || 1,
                      page_number: parseInt(page, 10) || 1,
                      document_id: docName,
                    });
                  }}
                  className="inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/25 font-mono text-xs font-semibold shadow-xs transition hover:scale-105 active:scale-95 cursor-pointer align-baseline"
                  title={`Inspect cited evidence in ${docName} (Page ${page})`}
                >
                  <FileText size={12} className="text-primary flex-shrink-0" />
                  <span className="truncate max-w-[180px]">{docName}</span>
                  <span className="text-[10px] opacity-75 font-normal">p.{page}</span>
                </button>
              );
            }

            if (href?.startsWith("#court-")) {
              const code = href.replace("#court-", "").toUpperCase();
              const courtColors = {
                SC: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
                CA: "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30",
                FHC: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-500/30",
                NIC: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
              };
              return (
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 mx-1 rounded-md border text-[11px] font-bold tracking-tight ${
                    courtColors[code] || "bg-primary/10 text-primary border-primary/20"
                  }`}
                  title={`Jurisdiction Authority: ${code}`}
                >
                  <Scale size={12} />
                  <span>{children}</span>
                </span>
              );
            }

            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-semibold text-primary underline decoration-primary/40 underline-offset-2 hover:decoration-primary"
              >
                {children}
                <ExternalLink size={12} className="opacity-70" />
              </a>
            );
          },
          code({ inline, className, children }) {
            const match = /language-(\w+)/.exec(className || "");

            if (!inline && match) {
              return <CodeBlock language={match[1]} value={String(children)} />;
            }

            return (
              <code className="rounded bg-background px-1.5 py-0.5 text-xs font-mono text-primary border border-border">
                {children}
              </code>
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownRenderer;