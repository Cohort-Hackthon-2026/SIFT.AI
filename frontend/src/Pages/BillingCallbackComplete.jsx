import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, AlertTriangle, LoaderCircle } from "lucide-react";
import { useBilling } from "../../store/billing";

const showToast = (message, type = "success") => {
  window.dispatchEvent(
    new CustomEvent("add-toast", {
      detail: {
        message,
        type,
        duration: 4000,
      },
    }),
  );
};

export default function BillingCallbackComplete() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("processing");
  const { refreshPlan, resetPaymentState } = useBilling();
  const reference = searchParams.get("reference") ?? searchParams.get("trxref");
  const verifiedRef = useRef(false);

  useEffect(() => {
    if (verifiedRef.current) return;
    verifiedRef.current = true;

    let redirectTimer = null;

    const handleCallback = async () => {
      if (!reference) {
        setStatus("error");
        showToast(
          "Payment verification did not return a reference. Redirecting to home.",
          "error",
        );
        redirectTimer = setTimeout(
          () => navigate("/", { replace: true }),
          1600,
        );
        return;
      }

      try {
        const result = await refreshPlan();
        if (result?.success) {
          setStatus("success");
          showToast(
            "Payment successful. Your subscription has been upgraded.",
            "success",
          );
          redirectTimer = setTimeout(
            () => navigate("/", { replace: true }),
            1600,
          );
          return;
        }
      } catch (error) {
        console.error("Billing callback verification failed:", error);
      }

      setStatus("error");
      showToast(
        "We could not confirm your upgrade. Redirecting to home.",
        "error",
      );
      redirectTimer = setTimeout(() => navigate("/", { replace: true }), 1600);
    };

    handleCallback();

    return () => {
      if (redirectTimer) clearTimeout(redirectTimer);
      resetPaymentState();
    };
  }, [navigate, reference, refreshPlan, resetPaymentState]);

  const content = {
    processing: {
      title: "Processing Payment",
      description: "Please wait while we confirm your subscription update.",
      icon: <LoaderCircle className="h-16 w-16 animate-spin text-primary" />,
      accent: "border-primary/30 bg-primary/5",
    },
    success: {
      title: "Payment Successful",
      description:
        "Your plan upgrade is now active. Redirecting you back to your account.",
      icon: <CheckCircle2 className="h-16 w-16 text-emerald-500" />,
      accent: "border-emerald-500/30 bg-emerald-500/5",
    },
    error: {
      title: "Something Went Wrong",
      description:
        "We could not confirm the payment callback. Please check your billing status in settings.",
      icon: <AlertTriangle className="h-16 w-16 text-amber-500" />,
      accent: "border-amber-500/30 bg-amber-500/5",
    },
  }[status];

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 px-4">
      <div
        className={`w-full max-w-md rounded-2xl border p-8 text-center shadow-2xl ${content.accent}`}
      >
        <div className="mb-6 flex justify-center">{content.icon}</div>
        <h1 className="text-2xl font-bold text-white">{content.title}</h1>
        <p className="mt-3 text-sm text-slate-300">{content.description}</p>
        <div className="mt-6 rounded-xl border border-white/10 bg-slate-900/40 px-4 py-3 text-xs text-slate-400">
          {searchParams.get("reference") || searchParams.get("trxref")
            ? `Reference: ${searchParams.get("reference") ?? searchParams.get("trxref")}`
            : "No reference received from the payment provider."}
        </div>
      </div>
    </div>
  );
}
