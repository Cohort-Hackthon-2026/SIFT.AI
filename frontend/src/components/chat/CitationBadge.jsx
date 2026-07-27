import { useCitation } from "../../../store/citation";

function CitationBadge({
    citation,
}) {
    const openCitation = useCitation(
        (state) => state.openCitation
    );

    return (
        <button
            onClick={() => openCitation(citation)}
            className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition hover:bg-primary/20"
        >
            {citation.label}
        </button>
    );
}

export default CitationBadge;