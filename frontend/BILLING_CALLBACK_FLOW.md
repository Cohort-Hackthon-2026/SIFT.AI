# Billing Callback Flow Documentation

## Overview

This document describes the payment callback flow for the Paystack integration. When a user upgrades their subscription tier, they are redirected to Paystack for payment completion. After payment, Paystack redirects the user back to your application via a callback URL configured on the backend.

---

## Complete Payment Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          1. User Initiates Upgrade                          │
│                  (Clicks "Upgrade to Starter/Pro" button)                    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    2. Frontend Calls startCheckout()                         │
│                  POST /api/v1/billing/checkout with:                        │
│                  - tier: "STARTER" | "PRO"                                  │
│                  - email: user's email                                      │
│                  - chambers_id: (optional) chambers to upgrade              │
│                                                                              │
│  Returns:                                                                    │
│  {                                                                           │
│    provider: "paystack",                                                    │
│    authorization_url: "https://checkout.paystack.com/...",                 │
│    reference: "sift_xxxxx",                                                │
│    amount_kobo: 6000000,                                                    │
│    ...                                                                       │
│  }                                                                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│            3. Frontend Redirects to Paystack Checkout Page                  │
│           window.location.href = res.authorization_url                      │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    4. User Completes Payment on Paystack                    │
│         (Enters card details, confirms payment, authenticates if needed)    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          5. Paystack Redirects to Callback URL (Backend Config)             │
│         Paystack: "https://yourdomain.com/billing/checkout/complete"        │
│                  ?reference=sift_xxxxx                                      │
│                                                                              │
│  This URL is configured via PAYSTACK_CALLBACK_URL env var on the backend   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│            6. Frontend Callback Page Receives Control                       │
│                                                                              │
│  This is the NEW page you need to create at that route                     │
│  URL received: /billing/checkout/complete?reference=sift_xxxxx             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│        7. Backend Webhook Processing (Happens in Background)                │
│                                                                              │
│  Paystack simultaneously sends a POST to /api/v1/billing/webhook            │
│  (HMAC-SHA512 signature verified)                                           │
│                                                                              │
│  On charge.success:                                                         │
│  - Extracts chambers_id, tier from transaction metadata                    │
│  - Updates chambers tier in database                                        │
│  - Creates subscription record                                             │
│  - Records audit log                                                       │
│  - Returns 200 OK to Paystack                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│         8. Frontend Polls for Tier Change (Already Implemented)             │
│                                                                              │
│  The BillingModal.jsx already has a polling mechanism:                     │
│  - Every 3 seconds, calls GET /api/v1/billing/plan                         │
│  - Compares old tier vs new tier                                           │
│  - If tier changed to target tier → Payment succeeded                       │
│  - Shows success toast, closes modal                                        │
│  - Polls up to 40 times (~2 minutes) then times out                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        9. Success - User Upgraded                           │
│                                                                              │
│  - Chambers tier is now STARTER/PRO                                         │
│  - New entitlements are active                                             │
│  - Billing modal closes                                                    │
│  - User is notified                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Callback Page Implementation

You need to create a new page/route to handle the callback. This page receives the user redirect from Paystack.

### Route Path Options

Choose one based on your routing structure:

**Option 1: React Component with React Router (Recommended)**

```
src/Pages/BillingCallbackComplete.jsx
```

**Option 2: Component in components directory**

```
src/components/billing/CallbackComplete.jsx
```

### Implementation Example

```jsx
// src/Pages/BillingCallbackComplete.jsx

import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useUI } from "../store/ui"; // or wherever your UI store is

export default function BillingCallbackComplete() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("processing"); // processing | success | error
  const { openUpgradeModal } = useUI();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Extract reference from URL query params
        const reference = searchParams.get("reference");

        if (!reference) {
          console.warn("No payment reference provided");
          setStatus("error");
          // Redirect after 2 seconds
          setTimeout(() => navigate("/billing"), 2000);
          return;
        }

        // Log the reference (for debugging)
        console.log("Payment reference:", reference);

        // Optional: Verify the reference with the backend
        // This is optional because the backend has already processed
        // the payment via the webhook, but you can verify if needed

        // For now, just show success and redirect
        setStatus("success");

        // Redirect to billing/settings page after 2 seconds
        setTimeout(() => {
          navigate("/settings");
        }, 2000);
      } catch (error) {
        console.error("Callback processing error:", error);
        setStatus("error");
        setTimeout(() => navigate("/settings"), 2000);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  // Render loading/success/error states
  if (status === "processing") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="mb-4">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Processing Payment
          </h1>
          <p className="text-slate-400">
            Please wait while we confirm your payment...
          </p>
        </div>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="mb-4">
            <div className="inline-block text-emerald-500">
              <svg
                className="w-16 h-16"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Payment Successful!
          </h1>
          <p className="text-slate-400 mb-4">
            Your subscription has been upgraded. Redirecting...
          </p>
          <p className="text-slate-500 text-sm">
            Redirecting to settings in 2 seconds...
          </p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="mb-4">
            <div className="inline-block text-red-500">
              <svg
                className="w-16 h-16"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">
            Something Went Wrong
          </h1>
          <p className="text-slate-400 mb-4">
            We couldn't process your payment callback.
          </p>
          <p className="text-slate-500 text-sm">
            Redirecting to settings in 2 seconds...
          </p>
        </div>
      </div>
    );
  }
}
```

### Add Route to React Router

In your main routing file (e.g., `App.jsx` or `main.jsx`):

```jsx
import BillingCallbackComplete from "./Pages/BillingCallbackComplete";

// Inside your router configuration:
<Route
  path="/billing/checkout/complete"
  element={<BillingCallbackComplete />}
/>;
```

---

## Security Considerations

### ✅ What's Already Secure

1. **Webhook Signature Verification**: Backend validates HMAC-SHA512 signature
2. **Backend Controls Callback URL**: `PAYSTACK_CALLBACK_URL` is configured on backend only
3. **No Direct Payment Processing on Frontend**: Frontend just receives redirect, doesn't process payment data
4. **Polling Verification**: Frontend independently verifies tier change via `/api/v1/billing/plan`

### ⚠️ What You Should Know

1. **The callback URL is public**: Anyone with the URL can visit it (they'll just see loading/success state)
2. **Reference Parameter is Not Sensitive**: The payment reference is not a secret; it's just metadata
3. **Payment Verification is on Backend**: The backend verifies payment with Paystack using HMAC signatures
4. **Polling is Your Verification**: Don't trust the callback URL alone—the polling mechanism verifies payment succeeded

---

## Database State After Payment

After Paystack sends the webhook, your database is updated:

```sql
-- In the 'subscriptions' table:
INSERT INTO subscriptions (
  chambers_id,
  tier,
  status,
  period_start,
  external_ref  -- Paystack reference (e.g., "sift_xxxxx")
) VALUES (
  'chambers_abc123',
  'PRO',
  'ACTIVE',
  NOW(),
  'sift_xyz789'
);

-- In the 'chambers' table:
UPDATE chambers SET tier = 'PRO' WHERE chambers_id = 'chambers_abc123';

-- In the 'audit' table:
INSERT INTO audit (user_id, action, detail) VALUES (
  'user_123',
  'BILLING_UPGRADE',
  '{"tier": "PRO", "reference": "sift_xyz789", "chambers_id": "chambers_abc123"}'
);
```

---

## Environment Configuration

### Backend (.env)

```env
# Paystack API Credentials
PAYSTACK_SECRET_KEY=sk_live_xxxxx_or_sk_test_xxxxx
PAYSTACK_PUBLIC_KEY=pk_live_xxxxx_or_pk_test_xxxxx

# ⭐ IMPORTANT: This is where you set the callback URL
# After payment, Paystack redirects the user here
PAYSTACK_CALLBACK_URL=https://yourdomain.com/billing/checkout/complete

# For development (localhost):
# PAYSTACK_CALLBACK_URL=http://localhost:5173/billing/checkout/complete
```

### Frontend (.env)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
```

---

## Troubleshooting

### Payment Completed But Tier Didn't Update

**Symptoms**: User sees "Payment Successful" but tier didn't change

**Causes**:

1. Webhook didn't reach the backend (network issue)
2. `PAYSTACK_SECRET_KEY` is incorrect (webhook verification fails)
3. Polling timeout (exceeded 40 attempts / ~2 minutes)

**Solutions**:

- Check backend logs for webhook processing errors
- Verify `PAYSTACK_SECRET_KEY` matches your Paystack account
- Check `/api/v1/billing/plan` endpoint manually to see current tier
- Extend polling in BillingModal.jsx if needed

### Callback URL Not Called

**Symptoms**: User completes payment but never sees the redirect page

**Causes**:

1. `PAYSTACK_CALLBACK_URL` is not set in backend
2. Callback URL is not publicly accessible
3. Route is not registered in frontend router

**Solutions**:

- Verify `PAYSTACK_CALLBACK_URL` is set in backend `.env`
- Test URL is reachable: `curl https://yourdomain.com/billing/checkout/complete`
- Verify route exists in React Router configuration

### Reference Parameter Missing

**Symptoms**: Callback page loads but shows error

**Causes**:

1. Paystack doesn't have the callback URL configured
2. Frontend router didn't catch the URL properly

**Solutions**:

- Check Paystack dashboard settings
- Ensure callback route comes before catch-all routes in router

---

## Testing

### Test Paystack Credentials (Sandbox)

```env
PAYSTACK_SECRET_KEY=sk_test_xxxxxx
PAYSTACK_PUBLIC_KEY=pk_test_xxxxxx
```

### Test Cards

Use these cards in Paystack's test environment:

- **Valid Card**: `4111 1111 1111 1111` | Exp: Any future date | CVV: Any 3 digits
- **Insufficient Funds**: `4000 0000 0000 0002`
- **3D Secure**: `4000 0100 0000 0019`

### Local Testing Flow

1. Start backend: `docker compose up` (from `backend/`)
2. Start frontend: `npm run dev` (from `frontend/`)
3. Set in backend `.env`:
   ```
   PAYSTACK_CALLBACK_URL=http://localhost:5173/billing/checkout/complete
   ```
4. Open billing modal, click upgrade
5. Redirect to Paystack checkout (use test card)
6. Complete payment
7. Verify redirect to callback page
8. Verify polling detects tier change

---

## API Endpoints Reference

### GET /api/v1/billing/plan

Returns current tier and entitlements

**Used By**: Polling mechanism to detect upgrade

**Response**:

```json
{
  "tier": "STARTER",
  "chambers_id": "chambers_abc123",
  "entitlements": { ... },
  "usage": { ... },
  "plans": { ... }
}
```

### POST /api/v1/billing/checkout

Initiates a payment transaction

**Request**:

```json
{
  "tier": "PRO",
  "email": "user@example.com",
  "chambers_id": "chambers_abc123"
}
```

**Response (Paystack)**:

```json
{
  "provider": "paystack",
  "authorization_url": "https://checkout.paystack.com/...",
  "reference": "sift_xxxxx",
  "amount_kobo": 6000000
}
```

### POST /api/v1/billing/webhook

Receives payment confirmation from Paystack (backend only, no frontend interaction)

**Triggered By**: Paystack after payment completion

**Verifies**: HMAC-SHA512 signature using `PAYSTACK_SECRET_KEY`

---

## Summary Checklist

- [ ] Read this entire document
- [ ] Understand the payment flow diagram
- [ ] Create `BillingCallbackComplete.jsx` component
- [ ] Add route to React Router configuration
- [ ] Verify `PAYSTACK_CALLBACK_URL` is in backend `.env`
- [ ] Test payment flow end-to-end with Paystack test cards
- [ ] Verify polling detects tier upgrade
- [ ] Handle error cases gracefully
