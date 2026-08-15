import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, AlertTriangle, LoaderCircle, ArrowRight } from "lucide-react";
import { useBilling } from "../../store/billing";
import { useProfile } from "../../store/profile";
import { useUI } from "../../store/ui";

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
  const [upgradedTier, setUpgradedTier] = useState(null);
  const { verifyPayment, refreshPlan, resetPaymentState } = useBilling();
  const { fetchProfile } = useProfile();
  const { closeBillingModal } = useUI();
  const reference = searchParams.get("reference") ?? searchParams.get("trxref");
  const verifiedRef = useRef(false);

  useEffect(() => {
    // Ensure the billing modal is dismissed when landing on callback
    closeBillingModal();
  }, [closeBillingModal]);

  useEffect(() => {
    if (verifiedRef.current) return;
    verifiedRef.current = true;

    let redirectTimer = null;

    const handleCallback = async () => {
      if (!reference) {
        setStatus("error");
        showToast(
          "Payment verification did not return a reference. Redirecting to settings.",
          "error",
        );
        redirectTimer = setTimeout(
          () => navigate("/settings", { replace: true }),
          2000,
        );
        return;
      }

      try {
        const result = await verifyPayment(reference);
        if (result?.success) {
          const tier = result.tier || "PRO";
          setUpgradedTier(tier);
          setStatus("success");
          closeBillingModal();
          await fetchProfile().catch(() => {});
          showToast(
            `Payment successful! Your subscription has been upgraded to ${tier}.`,
            "success",
          );
          redirectTimer = setTimeout(
            () => navigate("/settings", { replace: true }),
            1800,
          );
          return;
        }
      } catch (error) {
        console.error("Billing verification failed, attempting plan refresh fallback:", error);
      }

      try {
        const fallback = await refreshPlan();
        if (fallback?.success) {
          const tier = fallback.tier || "PRO";
          setUpgradedTier(tier);
          setStatus("success");
          closeBillingModal();
          await fetchProfile().catch(() => {});
          showToast(
            `Subscription updated to ${tier}.`,
            "success",
          );
          redirectTimer = setTimeout(
            () => navigate("/settings", { replace: true }),
            1800,
          );
          return;
        }
      } catch (fallbackError) {
        console.error("Plan refresh fallback failed:", fallbackError);
      }

      setStatus("error");
      showToast(
        "We could not confirm your upgrade. Redirecting to settings.",
        "error",
      );
      redirectTimer = setTimeout(() => navigate("/settings", { replace: true }), 2200);
    };

    handleCallback();

    return () => {
      if (redirectTimer) clearTimeout(redirectTimer);
      resetPaymentState();
    };
  }, [navigate, reference, verifyPayment, refreshPlan, resetPaymentState, fetchProfile, closeBillingModal]);

  const content = {
    processing: {
      title: "Verifying Payment",
      description: "Please wait while we confirm your subscription update with the payment gateway.",
      icon: <LoaderCircle className="h-16 w-16 animate-spin text-primary" />,
      accent: "border-primary/30 bg-primary/5",
    },
    success: {
      title: "Payment Successful",
      description: `Your ${upgradedTier || "plan"} upgrade is now active. Redirecting you to your practitioner profile and subscription dashboard.`,
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
          {reference
            ? `Reference: ${reference}`
            : "No reference received from payment gateway."}
        </div>

        <div className="mt-6">
          <button
            type="button"
            onClick={() => {
              closeBillingModal();
              navigate("/settings", { replace: true });
            }}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-textInverse shadow-lg shadow-primary/20 transition hover:opacity-90 active:scale-95"
          >
            <span>Go to Profile & Settings</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

