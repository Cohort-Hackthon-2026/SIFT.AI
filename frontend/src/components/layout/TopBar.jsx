import {
    FileText,
    ShieldCheck,
} from "lucide-react";

import ThemeToggle from "../theme/ThemeToggle";
import Button from "../ui/Button";
import ModeDropdown from "../theme/ModeDropdown";

function TopBar() {
    return (
        <header className="sticky top-0 z-50 border-b border-border bg-surface/80 backdrop-blur-xl">
            <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">

                <div className="flex items-center gap-3">

                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white">
                        <FileText size={20} />
                    </div>

                    <div>
                        <h1 className="text-lg font-semibold">
                            Sift AI
                        </h1>

                        <p className="text-xs text-textMuted">
                            Research Assistant
                        </p>
                    </div>

                </div>

                <div className="flex items-center gap-3">

                    {/* <Button
                        variant="secondary"
                        className="hidden sm:flex gap-2"
                    >
                        <ShieldCheck size={18} />
                        STRICT
                    </Button> */}

                    <ModeDropdown />

                    <ThemeToggle />

                </div>

            </div>
        </header>
    );
}

export default TopBar;