import { useState, useCallback } from "react";
import Toast from "./Toast";

function ToastProvider() {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "info", duration = 3000) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, message, type, duration }]);
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  return (
    <>
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            duration={toast.duration}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
      <div data-toast-context={{ addToast, removeToast }} />
    </>
  );
}

// Global toast context
let globalToastFn = null;

export function useToast() {
  const [id] = useState(() => crypto.randomUUID());

  return useCallback(
    (message, type = "info", duration = 3000) => {
      // This is a simple implementation that will work with our Toast component
      const event = new CustomEvent("add-toast", {
        detail: { message, type, duration },
      });
      window.dispatchEvent(event);
    },
    []
  );
}

export default ToastProvider;
