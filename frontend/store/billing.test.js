import test from "node:test";
import assert from "node:assert/strict";

const storage = new Map();
globalThis.sessionStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
  clear: () => storage.clear(),
};

const { useBilling } = await import("./billing.js");

test("startCheckout persists the chosen target tier before redirecting to Paystack", async () => {
  const { startCheckout, resetPaymentState } = useBilling.getState();

  storage.clear();
  resetPaymentState();

  await startCheckout({ tier: "STARTER", email: "test@example.com" });

  const saved = JSON.parse(sessionStorage.getItem("billing-storage") || "{}");
  assert.equal(saved.state?.lastCheckoutTier, "STARTER");
});
