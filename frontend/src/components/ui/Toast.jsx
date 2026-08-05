import { X, AlertCircle, CheckCircle2, Info } from "lucide-react";
import { useEffect, useState } from "react";

function Toast({ message, type = "info", duration = 3000, onClose }) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (duration === 0) return;
    
    const timer = setTimeout(() => {
      setIsVisible(false);
      onClose?.();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!isVisible) return null;

  const icons = {
    error: <AlertCircle size={20} />,
    success: <CheckCircle2 size={20} />,
    info: <Info size={20} />,
  };

  const styles = {
    error: "bg-error text-textInverse border-error/20",
    success: "bg-success text-textInverse border-success/20",
    info: "bg-primary text-textInverse border-primary/20",
  };

  return (
    <div
      className={`animate-slide-in fixed bottom-6 right-6 z-50 flex max-w-sm gap-3 rounded-2xl border p-4 shadow-lg ${styles[type]}`}
    >
      <div className="flex-shrink-0">{icons[type]}</div>
      <div className="flex-1">
        <p className="text-sm font-medium">{message}</p>
      </div>
      <button
        onClick={() => {
          setIsVisible(false);
          onClose?.();
        }}
        className="flex-shrink-0 opacity-70 transition hover:opacity-100"
      >
        <X size={18} />
      </button>
    </div>
  );
}

export default Toast;
