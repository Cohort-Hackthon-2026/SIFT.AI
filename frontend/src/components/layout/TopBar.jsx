import { FileSearch2, PanelLeftOpen, Globe2, Building2 } from "lucide-react";

import ThemeToggle from "../theme/ThemeToggle";
import ModeDropdown from "../theme/ModeDropdown";
import Button from "../ui/Button";

import { useAuth } from "@clerk/react";
import { useAuth as useLocalAuth } from "../../../store/auth";
import { useProfile } from "../../../store/profile";

function TopBar({ sidebarOpen, onToggleSidebar }) {
  const { isLoaded, isSignedIn } = useAuth();
  const openWelcome = useLocalAuth((state) => state.openWelcome);
  const profile = useProfile((state) => state.profile);

  const jurisdictionLabel = profile?.default_jurisdiction === "UK"
    ? "🇬🇧 UK Common Law"
    : profile?.default_jurisdiction === "US"
    ? "🇺🇸 United States"
    : profile?.default_jurisdiction === "GH"
    ? "🇬🇭 Ghana"
    : "🇳🇬 Nigeria (NWLR / Statutes)";

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-3 sm:px-6 lg:px-8">
        {/* Left side - Sidebar toggle at the edge */}
        <div className="flex items-center gap-3 sm:gap-5">
          {!sidebarOpen && (
            <button
              type="button"
              onClick={onToggleSidebar}
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-background text-text transition-all duration-200 hover:bg-primary/10 hover:border-primary active:scale-95"
              aria-label="Open sidebar"
              title="Open sidebar"
            >
              <PanelLeftOpen size={20} />
            </button>
          )}

          {/* Logo and branding */}
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-primary text-textInverse shadow-lg shadow-primary/20 transition-transform hover:scale-105">
              <FileSearch2 size={22} />
            </div>

            <div className="hidden sm:block">
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-text">SIFT.AI</h1>
                <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary uppercase tracking-wide">
                  Legal Precision
                </span>
              </div>
              <p className="text-xs text-textMuted">AI Research & Grounding</p>
            </div>
          </div>
        </div>

        {/* Center / Jurisdiction & Chambers pill (visible on md screens up) */}
        <div className="hidden md:flex items-center gap-2">
          <div
            className="flex items-center gap-1.5 rounded-full border border-border bg-background/80 px-3 py-1 text-xs font-medium text-text shadow-sm"
            title="Active Jurisdiction Context"
          >
            <Globe2 size={13} className="text-primary" />
            <span>{jurisdictionLabel}</span>
          </div>

          {profile?.role && (
            <div
              className="flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-xs font-medium text-primary shadow-sm"
              title="Professional Role"
            >
              <Building2 size={13} />
              <span>{profile.role.replace(/_/g, " ")}</span>
            </div>
          )}
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
