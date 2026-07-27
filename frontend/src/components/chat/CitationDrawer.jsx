import { X } from "lucide-react";

import CitationCard from "./CitationCard";

import { useCitation } from "../../../store/citation";

function CitationDrawer() {
    const open = useCitation(
        (state) => state.open
    );

    const citation = useCitation(
        (state) => state.citation
    );

    const closeCitation = useCitation(
        (state) => state.closeCitation
    );

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm">

            <div className="absolute right-0 top-0 h-screen w-full max-w-lg border-l border-border bg-surface shadow-2xl">

                <div className="flex items-center justify-between border-b border-border p-5">

                    <h2 className="text-lg font-semibold">
                        Evidence
                    </h2>

                    <button
                        onClick={closeCitation}
                        className="rounded-lg p-2 hover:bg-background"
                    >
                        <X size={18} />
                    </button>

                </div>

                <div className="overflow-y-auto p-6">

                    <CitationCard
                        citation={citation}
                    />

                </div>

            </div>

        </div>
    );
}

export default CitationDrawer;