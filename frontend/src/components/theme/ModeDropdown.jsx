import { ChevronDown, Check } from "lucide-react";
import { useState } from "react";
import { useSettings } from "../../../store/settings";

function ModeDropdown() {
    const [open, setOpen] = useState(false);

    const mode = useSettings((s) => s.mode);
    const modes = useSettings((s) => s.modes);
    const setMode = useSettings((s) => s.setMode);

    const current = modes.find(
        (item) => item.value === mode
    );

    return (
        <div className="relative">

            <button
                onClick={() => setOpen(!open)}
                className="flex h-11 items-center gap-2 rounded-xl border border-border bg-surface px-4 text-sm font-medium hover:bg-background"
            >
                {current.label}

                <ChevronDown size={16} />
            </button>

            {open && (
                <div className="absolute right-0 mt-2 w-72 rounded-2xl border border-border bg-surface shadow-xl">

                    {modes.map((item) => (
                        <button
                            key={item.value}
                            onClick={() => {
                                setMode(item.value);
                                setOpen(false);
                            }}
                            className="flex w-full items-start justify-between px-4 py-4 text-left hover:bg-background"
                        >
                            <div>

                                <p className="font-medium">
                                    {item.label}
                                </p>

                                <p className="mt-1 text-sm text-textMuted">
                                    {item.description}
                                </p>

                            </div>

                            {item.value === mode && (
                                <Check
                                    size={18}
                                    className="text-primary"
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