import { LogOut } from "lucide-react";

function SidebarFooter({ email, imageUrl, onLogout, isSigningOut = false }) {
  return (
    <div className="sticky bottom-0 border-t border-border bg-surface/95 p-4 backdrop-blur-xl">
      <div className="rounded-2xl border border-border bg-background/80 p-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {imageUrl ? <img src={imageUrl} alt="" className="h-full w-full rounded-xl object-cover" /> : email.slice(0, 2).toUpperCase()}
          </div>

          <div className="min-w-0 flex-1">
            <p className="text-xs text-textMuted">Signed in as</p>
            <p className="truncate text-sm font-medium text-text">{email}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onLogout}
          disabled={isSigningOut}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text transition hover:bg-background disabled:cursor-not-allowed disabled:opacity-60"
        >
          <LogOut size={16} />
          {isSigningOut ? "Signing out..." : "Logout"}
        </button>
      </div>
    </div>
  );
}

export default SidebarFooter;
