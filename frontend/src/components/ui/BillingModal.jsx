import React, { useEffect, useState } from "react";
import { X, Check } from "lucide-react";
import { useUI } from "../../../store/ui";
import { useBilling } from "../../../store/billing";
import Toast from "./Toast"; // Adjust path as needed

export default function BillingModal() {
  const { billingModalOpen, closeBillingModal } = useUI();
  const { plan, fetchPlan, startCheckout } = useBilling();

  const [loadingTier, setLoadingTier] = useState(null);
  const [toast, setToast] = useState(null);

  // Trigger fetch strictly when modal opens to avoid infinite loops
  useEffect(() => {
    if (billingModalOpen) {
      fetchPlan().catch((err) => {
        console.error("Failed to fetch billing plan:", err);
        setToast({
          message: "Failed to load current billing plan",
          type: "error",
        });
      });
    }
  }, [billingModalOpen]);

  // Polling mechanism
  useEffect(() => {
    if (!billingModalOpen) return;

    const interval = setInterval(() => {
      useBilling.getState().refreshPlan().catch(() => {});
    }, 3000);

    return () => clearInterval(interval);
  }, [billingModalOpen]);

  if (!billingModalOpen) return null;

  const handleUpgrade = async (tier) => {
    setLoadingTier(tier);
    try {
      const res = await startCheckout({ tier });
      if (res?.provider === "paystack" && res?.authorization_url) {
        window.location.href = res.authorization_url;
      } else {
        setToast({
          message: "Checkout created (dev mode). Upgrade will be finalized via webhook.",
          type: "info",
        });
      }
    } catch (err) {
      const errorMessage = err?.tierGate?.message || err?.message || String(err);
      setToast({
        message: errorMessage,
        type: "error",
      });
    } finally {
      setLoadingTier(null);
    }
  };

  const plans = [
    {
      tier: "FREE",
      label: "Free",
      price: "₦0",
      queryQuota: 50,
      docQuota: 20,
      exportQuota: 5,
      features: ["Strict mode only", "PDF export", "Up to 5 team members"],
    },
    {
      tier: "STARTER",
      label: "Starter",
      price: "₦15,000",
      queryQuota: 500,
      docQuota: 200,
      exportQuota: 100,
      features: ["Strict + Enhanced mode", "PDF & DOCX export", "Up to 5 team members"],
      cta: "Upgrade to Starter",
      highlight: true,
    },
    {
      tier: "PRO",
      label: "Pro",
      price: "₦60,000",
      queryQuota: 5000,
      docQuota: 2000,
      exportQuota: 1000,
      features: ["Strict + Enhanced mode", "PDF, DOCX, PPTX export", "Audit log", "Up to 25 team members"],
      cta: "Upgrade to Pro",
    },
  ];

  const currentTier = plan?.tier || "FREE";

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
        {/* Modal Outer Container */}
        <div className="relative flex max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-border bg-surface shadow-2xl text-text">
          
          {/* Fixed Header */}
          <div className="flex flex-shrink-0 items-center justify-between border-b border-border p-6 pb-4">
            <div>
              <h2 className="text-xl font-bold tracking-tight">Upgrade Your Plan</h2>
              <p className="mt-0.5 text-xs text-textMuted">Select the best plan for your document and query needs.</p>
            </div>
            <button
              onClick={closeBillingModal}
              className="rounded-full p-1.5 text-textMuted transition hover:bg-background hover:text-text"
            >
              <X size={20} />
            </button>
          </div>

          {/* Scrollable Content Area */}
          <div className="overflow-y-auto p-6 scrollbar-none [scrollbar-width:none] [-ms-overflow-style:none]">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {plans.map((p) => {
                const isCurrent = p.tier === currentTier;
                const isLoading = loadingTier === p.tier;

                return (
                  <div
                    key={p.tier}
                    className={`relative flex flex-col justify-between rounded-xl border p-5 transition-all ${
                      isCurrent
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : p.highlight
                        ? "border-primary/40 bg-background"
                        : "border-border bg-background"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-base font-semibold">{p.label}</span>
                        {isCurrent && (
                          <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-semibold text-primary">
                            Current
                          </span>
                        )}
                      </div>

                      <div className="my-3 flex items-baseline gap-1">
                        <span className="text-2xl font-bold text-primary">{p.price}</span>
                        <span className="text-xs text-textMuted">/month</span>
                      </div>

                      {/* Quotas */}
                      <div className="mb-4 rounded-lg border border-border/50 bg-surface p-3 text-xs">
                        <span className="mb-1 block font-medium text-textMuted">Monthly Quotas:</span>
                        <ul className="space-y-1 font-medium">
                          <li>• {p.queryQuota.toLocaleString()} queries</li>
                          <li>• {p.docQuota.toLocaleString()} documents</li>
                          <li>• {p.exportQuota.toLocaleString()} exports</li>
                        </ul>
                      </div>

                      {/* Features */}
                      <div className="mb-4">
                        <span className="mb-2 block text-xs font-medium text-textMuted">Features included:</span>
                        <ul className="space-y-1.5 text-xs">
                          {p.features.map((f, i) => (
                            <li key={i} className="flex items-center gap-2">
                              <Check size={14} className="flex-shrink-0 text-primary" />
                              <span>{f}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Button Action */}
                    <div className="pt-2">
                      {isCurrent ? (
                        <button
                          disabled
                          className="w-full cursor-not-allowed rounded-lg bg-border py-2 text-xs font-semibold text-textMuted"
                        >
                          Active Plan
                        </button>
                      ) : p.cta ? (
                        <button
                          onClick={() => handleUpgrade(p.tier)}
                          disabled={isLoading}
                          className="w-full rounded-lg bg-primary py-2 text-xs font-semibold text-textInverse transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isLoading ? "Processing..." : p.cta}
                        </button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      </div>

      {/* Toast Notification Container */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </>
  );
}