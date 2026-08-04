import { FileSearch2 } from "lucide-react";

import ThemeToggle from "../theme/ThemeToggle";
import ModeDropdown from "../theme/ModeDropdown";
import Button from "../ui/Button";

import { useAuth } from "@clerk/react";
import { useAuth as useLocalAuth } from "../../../store/auth";

function TopBar() {
  const { isLoaded, isSignedIn, signOut } = useAuth();
  const openWelcome = useLocalAuth((state) => state.openWelcome);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-textInverse shadow-lg shadow-primary/20">
            <FileSearch2 size={22} />
          </div>

          <div>
            <h1 className="text-lg font-semibold text-text">Sift AI</h1>
            <p className="text-xs text-textMuted">AI Research Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ModeDropdown />

           {isLoaded && !isSignedIn && (
            <Button variant="secondary" onClick={openWelcome}>
              Sign In
            </Button>
          )}

          {isLoaded && isSignedIn && (
            <Button variant="secondary" onClick={() => signOut()}>
              Log out
            </Button>
          )}
          
          <ThemeToggle />

          {/* {isLoaded && !isSignedIn && (
            <Button variant="secondary" onClick={openWelcome}>
              Sign In
            </Button>
          )}

          {isLoaded && isSignedIn && (
            <Button variant="secondary" onClick={() => signOut()}>
              Log out
            </Button>
          )} */}
        </div>
      </div>
    </header>
  );
}

export default TopBar;
