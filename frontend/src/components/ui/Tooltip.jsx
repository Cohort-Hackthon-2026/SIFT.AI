import { useState } from "react";

function Tooltip({
    children,
    text,
}) {
    const [open, setOpen] = useState(false);

    return (
        <div
            className="relative inline-flex"
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}
        >
            {children}

            {open && (
                <div className="absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text shadow-lg">
                    {text}
                </div>
            )}
        </div>
    );
}

export default Tooltip;