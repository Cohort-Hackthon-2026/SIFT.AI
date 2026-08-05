import { AlertCircle } from "lucide-react";

function ErrorMessage({ message, children, dismissible = false, onDismiss }) {
  return (
    <div className="rounded-2xl border border-error/30 bg-error/10 p-4">
      <div className="flex gap-3">
        <div className="flex-shrink-0 pt-0.5">
          <AlertCircle size={20} className="text-error" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-error">
            {message || children}
          </p>
        </div>
        {dismissible && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 text-error/70 transition hover:text-error"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}

export default ErrorMessage;
