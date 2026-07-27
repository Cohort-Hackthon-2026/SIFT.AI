function CitationCard({
    citation,
}) {
    if (!citation) return null;

    return (
        <div className="space-y-5">

            <div>

                <h3 className="text-lg font-semibold">
                    {citation.document}
                </h3>

                <p className="mt-1 text-sm text-textMuted">
                    Page {citation.page}
                </p>

            </div>

            <div className="rounded-2xl bg-background p-4 leading-8">

                {citation.content}

            </div>

        </div>
    );
}

export default CitationCard;