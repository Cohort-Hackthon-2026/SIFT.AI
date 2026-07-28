import {
    Brain,
    FileSearch,
    ShieldCheck,
} from "lucide-react";

function EmptyState() {
    return (
        <div className="flex flex-1 flex-col items-center justify-center py-16 text-center">

            <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10">
                <Brain
                    size={42}
                    className="text-primary"
                />
            </div>

            <h2 className="mt-8 text-4xl font-bold">
                Welcome to Sift AI
            </h2>

            <p className="mt-4 max-w-xl leading-8 text-textMuted">
                Upload your documents, ask questions, and receive
                accurate answers backed by citations from your PDFs
                and trusted sources.
            </p>

            <div className="mt-12 grid w-full max-w-3xl gap-4 md:grid-cols-3">

                <div className="rounded-2xl border border-border bg-surface p-6">
                    <FileSearch
                        className="mb-4 text-primary"
                        size={24}
                    />

                    <h3 className="font-semibold">
                        Document Search
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-textMuted">
                        Search multiple PDFs with semantic retrieval.
                    </p>
                </div>

                <div className="rounded-2xl border border-border bg-surface p-6">
                    <ShieldCheck
                        className="mb-4 text-primary"
                        size={24}
                    />

                    <h3 className="font-semibold">
                        Strict Citations
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-textMuted">
                        Every answer is backed by evidence you can inspect.
                    </p>
                </div>

                <div className="rounded-2xl border border-border bg-surface p-6">
                    <Brain
                        className="mb-4 text-primary"
                        size={24}
                    />

                    <h3 className="font-semibold">
                        AI Research
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-textMuted">
                        Switch to Enhanced Mode to combine PDFs with live web knowledge.
                    </p>
                </div>

            </div>

        </div>
    );
}

export default EmptyState;