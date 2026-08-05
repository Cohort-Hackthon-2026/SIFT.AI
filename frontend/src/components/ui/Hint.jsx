import { Info } from "lucide-react";

function Hint({ children, className = "" }) {
  return (
    <div className={`flex gap-2 rounded-xl border border-border bg-surface p-3 text-sm text-textMuted ${className}`}>
      <div className="flex-shrink-0 pt-0.5">
        <Info size={16} className="text-textMuted" />
      </div>
      <div>{children}</div>
    </div>
  );
}

export default Hint;
