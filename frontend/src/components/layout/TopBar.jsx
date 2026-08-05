import { FileSearch2, PanelLeftOpen, PanelLeftClose } from "lucide-react";

import ThemeToggle from "../theme/ThemeToggle";
import ModeDropdown from "../theme/ModeDropdown";
import Button from "../ui/Button";

import { useAuth } from "@clerk/react";
import { useAuth as useLocalAuth } from "../../../store/auth";

function TopBar({ sidebarOpen, onToggleSidebar, onCloseSidebar }) {
  const { isLoaded, isSignedIn } = useAuth();
  const openWelcome = useLocalAuth((state) => state.openWelcome);

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-3 sm:px-6 lg:px-8">
        {/* Left side - Sidebar toggle at the edge */}
        <div className="flex items-center gap-4 sm:gap-6">
          <button
            type="button"
            onClick={onToggleSidebar}
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-background text-text transition-all duration-200 hover:bg-primary/10 hover:border-primary active:scale-95"
            aria-label="Toggle sidebar"
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            {sidebarOpen ? (
              <PanelLeftClose size={20} />
            ) : (
              <PanelLeftOpen size={20} />
            )}
          </button>

          {/* Logo and branding */}
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-primary text-textInverse shadow-lg shadow-primary/20 transition-transform hover:scale-105">
              <FileSearch2 size={22} />
            </div>

            <div className="hidden sm:block">
              <h1 className="text-lg font-semibold text-text">Sift AI</h1>
              <p className="text-xs text-textMuted">AI Research Assistant</p>
            </div>
          </div>
        </div>

        {/* Right side - Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          <ModeDropdown />

          {isLoaded && !isSignedIn && (
            <Button variant="secondary" onClick={openWelcome} className="text-sm sm:text-base">
              Sign In
            </Button>
          )}

          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

export default TopBar;
