/**
 * Intelligent Chat Title Generator
 * Derives concise, descriptive legal titles from queries and prompts.
 */
export function generateChatTitle(query, fallback = "Legal Research") {
  if (!query || typeof query !== "string") return fallback;

  let cleaned = query.replace(/[\r\n\t]+/g, " ").trim();
  if (!cleaned) return fallback;

  // Remove leading conversational query prefixes
  const prefixes = [
    /^can you (please )?(explain|tell me about|summarize|summarise|analyze|analyse|clarify)\s+/i,
    /^could you (please )?(explain|tell me about|summarize|summarise|analyze|analyse|clarify)\s+/i,
    /^please (explain|tell me about|summarize|summarise|analyze|analyse|clarify)\s+/i,
    /^what (is|are|was|were) (the )?/i,
    /^what does\s+/i,
    /^how (does|do|can|is)\s+/i,
    /^is it legal to\s+/i,
    /^give me (a )?(summary of )?/i,
    /^summarize (the )?/i,
    /^summarise (the )?/i,
    /^tell me about (the )?/i,
    /^i want to know about (the )?/i,
    /^explain (the )?/i,
    /^find (the )?(legal )?(precedents for )?/i,
  ];

  for (const prefix of prefixes) {
    if (prefix.test(cleaned)) {
      cleaned = cleaned.replace(prefix, "").trim();
      break;
    }
  }

  // Capitalize the first letter
  if (cleaned.length > 0) {
    cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  }

  // Strip trailing question marks or punctuation
  cleaned = cleaned.replace(/[?.:;!]+$/, "").trim();

  // Truncate at word boundary (max ~42 chars)
  if (cleaned.length > 42) {
    const truncated = cleaned.slice(0, 42);
    const lastSpace = truncated.lastIndexOf(" ");
    if (lastSpace > 15) {
      cleaned = truncated.slice(0, lastSpace) + "...";
    } else {
      cleaned = truncated + "...";
    }
  }

  return cleaned || fallback;
}
