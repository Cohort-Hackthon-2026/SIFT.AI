# Frontend Fixes - Role Selection & Billing Modal Flow

## Issues Fixed

### 1. **Role Selection Modal Not Showing on Login**
**Problem**: The `hasRole()` function was being destructured incorrectly from the store. It's a method, not a reactive value, so the effect wasn't triggering properly.

**Fix** [App.jsx](frontend/src/App.jsx#L30-L40):
- Changed to destructure `profile`, `fetchProfile`, and `profileLoading` directly
- Now checks `profile.role && profile.role.trim() !== ''` directly instead of calling `hasRole()`
- Also added `profileLoading` to track when profile fetch completes
- Effect now properly triggers when profile loads and has no role

**Code**:
```javascript
const { profile, fetchProfile, loading: profileLoading } = useProfile();

useEffect(() => {
  if (isLoaded && isSignedIn && profile && !profileLoading) {
    const hasRole = profile.role && profile.role.trim() !== '';
    if (!hasRole) {
      openRoleSelectionModal();
    }
  }
}, [isLoaded, isSignedIn, profile, profileLoading, openRoleSelectionModal]);
```

### 2. **Billing Modal Not Showing After Role Selection**
**Problem**: There was no trigger to open the billing modal after role was selected.

**Fix** [App.jsx](frontend/src/App.jsx#L50-L56):
- Added separate effect that watches `roleSelectionModalOpen` state
- When role modal closes AND profile now has a role, billing modal opens
- Provides natural flow: Role Selection → Billing → Main App

**Code**:
```javascript
useEffect(() => {
  if (!roleSelectionModalOpen && profile && profile.role && profile.role.trim() !== '') {
    openBillingModal();
  }
}, [roleSelectionModalOpen, profile, openBillingModal]);
```

### 3. **Billing Plan Not Fetching**
**Problem**: 
- BillingModal only fetched plan if it wasn't already loaded (`!plan`)
- Sidebar didn't fetch plan at all
- This caused the "Upgrade" button to not show

**Fix** [BillingModal.jsx](frontend/src/components/ui/BillingModal.jsx#L8-L10):
```javascript
useEffect(() => {
  if (billingModalOpen) {
    // Always fetch plan when modal opens
    fetchPlan().catch((err) => console.error('Failed to fetch billing plan:', err));
  }
}, [billingModalOpen, fetchPlan]);
```

**Fix** [Sidebar.jsx](frontend/src/components/layout/Sidebar.jsx#L35-L43):
```javascript
const { plan, fetchPlan } = useBilling();

useEffect(() => {
  if (isSignedIn) {
    void loadChats();
    // Fetch billing plan for the upgrade button
    fetchPlan().catch(() => {});
  } else {
    useChat.getState().setChats([]);
    useChat.getState().setActiveChatId(null);
    useChat.getState().clearMessages();
  }
}, [isSignedIn, loadChats, fetchPlan]);
```

## User Flow Now Works As:

1. **User signs in** → Clerk redirects to app
2. **App fetches profile** → `GET /api/v1/me/profile`
3. **Profile loads without role** → Role Selection Modal appears (required, cannot skip)
4. **User selects role** → `PUT /api/v1/me/profile` with `{ role: "ASSOCIATE" }` (example)
5. **Role modal closes** → Profile store updates
6. **App detects role now exists** → Opens Billing Modal automatically
7. **Billing modal fetches plan** → `GET /api/v1/billing/plan`
8. **User chooses tier** → `POST /api/v1/billing/checkout { tier: "STARTER" }`
9. **Redirects to Paystack** (or mock confirmation in dev)
10. **User returns after payment** → Billing modal polls plan every 3 seconds
11. **Tier updates** → Sidebar "Upgrade" button disappears (no longer FREE tier)

## API Endpoints Being Called (per OpenAPI schema)

### Profile
- **GET** `/api/v1/me/profile` → Returns `ProfileResponse` with `role` field
- **PUT** `/api/v1/me/profile` → Accepts `UpdateProfileRequest` body `{ role: string }`

### Billing
- **GET** `/api/v1/billing/plan` → Returns plan info with `tier`, `usage`, `plans`
- **POST** `/api/v1/billing/checkout` → Accepts `CheckoutRequest` body `{ tier: string, chambers_id?: string, email?: string, callback_url?: string }`

## Key State Management

### App.jsx Dependencies Fixed:
```javascript
// Before (broken):
const { profile, hasRole } = useProfile();  // hasRole is function, not value
const { openRoleSelectionModal } = useUI();

useEffect(() => {
  if (...profile && !hasRole()) {  // hasRole() called in render
    ...
  }
}, [..., hasRole, ...]);  // hasRole is function ref, never changes


// After (correct):
const { profile, fetchProfile, loading: profileLoading } = useProfile();
const { openRoleSelectionModal, roleSelectionModalOpen, openBillingModal } = useUI();

useEffect(() => {
  if (isLoaded && isSignedIn) {
    fetchProfile().catch(() => {});  // Actually call the fetch
  }
}, [isLoaded, isSignedIn, ..., fetchProfile]);

useEffect(() => {
  if (isLoaded && isSignedIn && profile && !profileLoading) {
    const hasRole = profile.role && profile.role.trim() !== '';  // Check value
    if (!hasRole) {
      openRoleSelectionModal();
    }
  }
}, [isLoaded, isSignedIn, profile, profileLoading, openRoleSelectionModal]);

useEffect(() => {
  // Trigger billing after role is saved
  if (!roleSelectionModalOpen && profile && profile.role?.trim()) {
    openBillingModal();
  }
}, [roleSelectionModalOpen, profile, openBillingModal]);
```

## Testing Checklist

- [ ] Sign in with Clerk
- [ ] Role modal appears automatically (cannot close without selecting)
- [ ] Select a role and click "Continue"
- [ ] Profile saved to backend (`PUT /api/v1/me/profile`)
- [ ] Role modal closes
- [ ] Billing modal opens automatically
- [ ] Billing modal shows 3 tiers with usage data
- [ ] Sidebar shows "Upgrade to Premium" button (because tier is FREE)
- [ ] Click sidebar upgrade button → Billing modal opens
- [ ] Click "Upgrade to PRO" → Redirects to Paystack (or mock confirmation)
- [ ] After payment, plan updates (tier changes from FREE to PRO)
- [ ] Sidebar "Upgrade" button disappears (no longer on FREE tier)

## Files Modified

1. [frontend/src/App.jsx](frontend/src/App.jsx) - Fixed role checking and modal flow
2. [frontend/src/components/ui/BillingModal.jsx](frontend/src/components/ui/BillingModal.jsx) - Always fetch plan on open
3. [frontend/src/components/layout/Sidebar.jsx](frontend/src/components/layout/Sidebar.jsx) - Fetch billing plan on user signin
4. No backend changes needed - all endpoints are correct per OpenAPI docs

## Dev Server Status

- **Running on**: http://localhost:5175 (or next available port)
- **Build Status**: ✅ No errors
- **Compile Status**: ✅ All imports resolved

## Next Steps

1. **Test the flow locally** at http://localhost:5175
2. **Sign in with Clerk** (configured in `.env`)
3. **Verify modals appear in order**: Role → Billing
4. **Test billing**: Click "Upgrade" and complete Paystack checkout
5. **Verify state updates**: Plan tier should change after payment

---

**Note**: All API endpoints match the OpenAPI schema at http://localhost:8000/docs. If any endpoint returns unexpected format, check backend implementation against the schema.
