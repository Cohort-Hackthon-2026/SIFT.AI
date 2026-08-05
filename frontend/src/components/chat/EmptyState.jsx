import {
    Brain,
    FileSearch,
    ShieldCheck,
} from "lucide-react";

function EmptyState() {
    return (
        <div className="flex flex-1 flex-col items-center justify-center py-8 sm:py-12 lg:py-16 text-center px-4">
            <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-3xl bg-primary/10">
                <Brain
                    size={32}
                    className="sm:block hidden text-primary"
                />
                <Brain
                    size={24}
                    className="sm:hidden text-primary"
                />
            </div>

            <h2 className="mt-6 sm:mt-8 text-2xl sm:text-3xl lg:text-4xl font-bold text-text">
                Welcome to Sift AI
            </h2>

            <p className="mt-3 sm:mt-4 max-w-xl leading-relaxed text-sm sm:text-base text-textMuted">
                Upload your documents, ask questions, and receive
                accurate answers backed by citations from your PDFs
                and trusted sources.
            </p>

            <div className="mt-8 sm:mt-12 grid w-full max-w-3xl gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-3">
                <div className="rounded-2xl border border-border bg-surface p-4 sm:p-6">
                    <FileSearch
                        className="mb-3 sm:mb-4 text-primary mx-auto"
                        size={24}
                    />

                    <h3 className="font-semibold text-sm sm:text-base text-text">
                        Document Search
                    </h3>

                    <p className="mt-2 text-xs sm:text-sm leading-5 sm:leading-6 text-textMuted">
                        Search multiple PDFs with semantic retrieval.
                    </p>
                </div>

                <div className="rounded-2xl border border-border bg-surface p-4 sm:p-6">
                    <ShieldCheck
                        className="mb-3 sm:mb-4 text-primary mx-auto"
                        size={24}
                    />

                    <h3 className="font-semibold text-sm sm:text-base text-text">
                        Strict Citations
                    </h3>

                    <p className="mt-2 text-xs sm:text-sm leading-5 sm:leading-6 text-textMuted">
                        Every answer is backed by evidence you can inspect.
                    </p>
                </div>

                <div className="rounded-2xl border border-border bg-surface p-4 sm:p-6">
                    <Brain
                        className="mb-3 sm:mb-4 text-primary mx-auto"
                        size={24}
                    />

                    <h3 className="font-semibold text-sm sm:text-base text-text">
                        AI Research
                    </h3>

                    <p className="mt-2 text-xs sm:text-sm leading-5 sm:leading-6 text-textMuted">
                        Switch to Enhanced Mode to combine PDFs with live web knowledge.
                    </p>
                </div>
            </div>
        </div>
    );
}

export default EmptyState;