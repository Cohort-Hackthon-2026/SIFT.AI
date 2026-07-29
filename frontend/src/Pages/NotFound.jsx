import { Link } from "react-router-dom";
import { SearchX } from "lucide-react";

function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="w-full max-w-md rounded-3xl border border-border bg-surface p-10 text-center shadow-sm">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10">
          <SearchX className="h-10 w-10 text-primary" />
        </div>

        <p className="mt-8 text-sm font-medium tracking-widest text-primary uppercase">
          Error 404
        </p>

        <h1 className="mt-3 text-3xl font-bold text-text">
          Page not found
        </h1>

        <p className="mt-4 leading-7 text-textMuted">
          The page you're looking for doesn't exist or may have been moved.
          Continue chatting with Sift AI from the main workspace.
        </p>

        <div className="mt-10 flex justify-center">
          <Link
            to="/"
            className="rounded-xl bg-primary px-6 py-3 font-medium text-text-inverse transition-colors hover:bg-primary-hover"
          >
            Back to Chat
          </Link>
        </div>
      </div>
    </main>
  );
}

export default NotFound;