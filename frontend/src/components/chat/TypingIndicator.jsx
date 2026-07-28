function TypingIndicator() {
    return (
        <div className="flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-3 w-fit">
            <span className="h-2 w-2 animate-bounce rounded-full bg-primary"></span>

            <span
                className="h-2 w-2 animate-bounce rounded-full bg-primary"
                style={{ animationDelay: ".15s" }}
            />

            <span
                className="h-2 w-2 animate-bounce rounded-full bg-primary"
                style={{ animationDelay: ".3s" }}
            />
        </div>
    );
}

export default TypingIndicator;