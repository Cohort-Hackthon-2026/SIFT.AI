import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../../store/theme";

function ThemeToggle() {
    const theme = useTheme((state) => state.theme);
    const toggleTheme = useTheme((state) => state.toggleTheme);

    return (
        <button
            onClick={toggleTheme}
            className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-surface text-text transition-all duration-200 hover:bg-background"
            aria-label="Toggle theme"
        >
            {theme === "dark" ? (
                <Sun size={18} />
            ) : (
                <Moon size={18} />
            )}
        </button>
    );
}

export default ThemeToggle;