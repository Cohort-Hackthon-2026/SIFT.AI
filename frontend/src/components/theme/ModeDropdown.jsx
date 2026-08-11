import { ChevronDown, Check, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/react";
import { useSettings } from "../../../store/settings";

function ModeDropdown() {
    const [open, setOpen] = useState(false);
    const rootRef = useRef(null);
    const { isSignedIn } = useAuth();

    const mode = useSettings((s) => s.mode);
    const modes = useSettings((s) => s.modes);
    const setMode = useSettings((s) => s.setMode);

    const current = modes.find(
        (item) => item.value === mode
    );

    useEffect(() => {
        const close = (event) => {
            if (!rootRef.current?.contains(event.target)) setOpen(false);
        };
        document.addEventListener("pointerdown", close);
        return () => document.removeEventListener("pointerdown", close);
    }, []);

    return (
        <div className="relative" ref={rootRef}>
            <button
                onClick={() => setOpen(!open)}
                className={`flex h-11 items-center gap-2 rounded-xl border px-4 text-sm font-medium transition-all duration-200 ${
                    mode
                        ? "border-border bg-surface hover:bg-background active:scale-95"
                        : "border-warning/50 bg-warning/5 text-warning hover:bg-warning/10 hover:border-warning"
                }`}
            >
                {mode ? (
                    <>
                        {current?.label}
                        <ChevronDown size={16} />
                    </>
                ) : (
                    <>
                        <Zap size={16} />
                        <span>Select mode</span>
                        <ChevronDown size={16} />
                    </>
                )}
            </button>

            {open && (
                <div className="absolute right-0 mt-2 w-80 rounded-2xl border border-border bg-surface shadow-xl z-50">
                    {modes.map((item) => (
                        <button
                            key={item.value}
                            onClick={() => {
                                if (item.value === "enhanced" && !isSignedIn) {
                                    window.addToast?.("Please sign in to use Enhanced mode.", "info", 4000);
                                    setOpen(false);
                                    return;
                                }
                                setMode(item.value);
                                setOpen(false);
                            }}
                            className={`flex w-full items-start justify-between px-4 py-4 text-left transition-colors ${
                                item.value === mode
                                    ? "bg-primary/10"
                                    : "hover:bg-background"
                            }`}
                        >
                            <div>
                                <p className="font-medium text-text">
                                    {item.label}
                                </p>

                                <p className="mt-1 text-sm text-textMuted">
                                    {item.description}
                                </p>
                            </div>

                            {item.value === mode && (
                                <Check
                                    size={18}
                                    className="mt-1 flex-shrink-0 text-primary"
                                />
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

export default ModeDropdown;
