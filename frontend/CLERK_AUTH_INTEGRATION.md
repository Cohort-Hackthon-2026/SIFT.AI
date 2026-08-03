# Clerk Auth Integration Guide (Frontend)

The backend now requires every `/api/v1/documents*` and `/api/v1/audio/transcribe`
request to carry a valid Clerk session token. There are currently **zero auth
pages, routes, or Clerk setup anywhere in this frontend** - this doc covers
building that from scratch. Read `FRONTEND_INTEGRATION.md` first for the
non-auth endpoint wiring; this doc slots in alongside it.

Account model for now: **individual accounts only** (one lawyer, one set of
documents - no firm/organization support yet). Nothing below uses Clerk
Organizations; that's a deliberate, revisitable choice, not an oversight.

## 1. Get your publishable key

You'll need a Clerk account and application already created (see
`backend/HUMAN_RUNBOOK.md`'s Auth section - the backend dev sets up
`CLERK_JWKS_URL`/`CLERK_ISSUER` from the same Clerk application). From the
Clerk Dashboard, copy the **Publishable key** (starts with `pk_test_...` or
`pk_live_...` - safe to expose client-side, unlike the secret key).

## 2. Install the SDK

```bash
npm install @clerk/react
```

**Important:** the package is `@clerk/react`, not `@clerk/clerk-react`.
Clerk renamed the React SDK in their "Core 3" release (March 2026) -
`@clerk/clerk-react` still exists on npm but is explicitly marked
unsupported ("Please use @clerk/react instead"). A lot of older tutorials
and Stack Overflow answers still reference the old name; don't follow them.

## 3. Environment variable

Create `frontend/.env` (there's no `.env.example` in this repo yet - add
one alongside this):

```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
VITE_API_BASE_URL=http://localhost:8000
```

## 4. Wrap the app in `<ClerkProvider>`

In `frontend/src/main.jsx` (the Vite entry point):

```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ClerkProvider } from "@clerk/react";
import App from "./App.jsx";
import "./index.css";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing VITE_CLERK_PUBLISHABLE_KEY - check frontend/.env");
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
      <App />
    </ClerkProvider>
  </StrictMode>,
);
```

## 5. Add sign-in/sign-up routes

`react-router-dom` v7 is already installed and used in `App.jsx`
(`BrowserRouter`/`Routes`/`Route`) - build on that rather than introducing a
second routing approach. Use Clerk's prebuilt `<SignIn>`/`<SignUp>`
components rather than hand-building forms; they already implement exactly
what you described - email/password with name fields, plus a "Continue with
Google" option - as soon as you enable Google in the Clerk Dashboard
(Configure -> SSO Connections). No custom form code needed for MVP.

```jsx
// src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SignIn, SignUp } from "@clerk/react";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import Chat from "./Pages/Chat";
import NotFound from "./Pages/NotFound";

function App() {
  // ...existing theme effect...

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/sign-in/*"
          element={<SignIn routing="path" path="/sign-in" signUpUrl="/sign-up" />}
        />
        <Route
          path="/sign-up/*"
          element={<SignUp routing="path" path="/sign-up" signInUrl="/sign-in" />}
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
```

Note the `/*` on the sign-in/sign-up routes and `routing="path"` - Clerk's
components manage their own sub-steps (password entry, verification code,
etc.) as nested paths under the same route, so they need to catch everything
under `/sign-in` and `/sign-up`, not just the exact path.

## 6. Protect the chat route

Create `src/components/auth/ProtectedRoute.jsx`:

```jsx
import { useAuth } from "@clerk/react";
import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ children }) {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return null; // or a loading spinner - avoid a flash of the sign-in page
  }

  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace />;
  }

  return children;
}
```

The `isLoaded` check matters: Clerk needs a moment to determine auth state on
first load, and redirecting before it's ready would bounce an already-signed-in
user to `/sign-in` for a flash before sending them back.

## 7. Attach the token to every API request

This is the piece that actually connects auth to the backend work already
done. Zustand stores (`store/upload.js`, `store/documents.js`, etc.) can't
call React hooks directly, so `useAuth()`'s `getToken()` can't be called
from inside them. Rather than threading a `token` argument through every
single store action and every call site, use a small bridge: one component
that *can* call `useAuth()` hands the token getter to a plain module, and
`api.js` pulls from that module itself. This keeps every store action
looking exactly like the plain pre-auth version - no `token` parameters
anywhere except inside `api.js`.

**`src/lib/authBridge.js`** (new file):

```js
let getTokenFn = null;

export function setTokenGetter(fn) {
  getTokenFn = fn;
}

export async function getAuthToken() {
  if (!getTokenFn) {
    // Happens if something calls the API before ClerkProvider has mounted -
    // shouldn't occur in practice since ProtectedRoute blocks the chat UI
    // until Clerk is loaded, but fail loudly rather than silently.
    throw new Error("Auth isn't ready yet");
  }
  return getTokenFn();
}
```

**`src/components/auth/AuthBridge.jsx`** (new file) - the only place besides
`ProtectedRoute` that touches `useAuth()` directly:

```jsx
import { useEffect } from "react";
import { useAuth } from "@clerk/react";
import { setTokenGetter } from "../../lib/authBridge";

export default function AuthBridge() {
  const { getToken } = useAuth();

  useEffect(() => {
    setTokenGetter(getToken);
  }, [getToken]);

  return null;
}
```

Render it once, inside `<ClerkProvider>` but outside/above `<Routes>` in
`App.jsx`, so it's mounted regardless of which route is active:

```jsx
<BrowserRouter>
  <AuthBridge />
  <Routes>{/* ...existing routes... */}</Routes>
</BrowserRouter>
```

**`api.js`** pulls the token itself instead of accepting one as a parameter:

```js
// src/lib/api.js
import { getAuthToken } from "./authBridge";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const token = await getAuthToken();
  const headers = { ...options.headers, Authorization: `Bearer ${token}` };
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON - keep statusText
    }
    throw new Error(detail);
  }

  return response.status === 204 ? null : response.json();
}

export const api = {
  uploadDocument: (formData) =>
    request("/api/v1/documents/upload", { method: "POST", body: formData }),

  listDocuments: () => request("/api/v1/documents"),

  deleteDocument: (documentId) =>
    request(`/api/v1/documents/${documentId}`, { method: "DELETE" }),

  transcribeAudio: (formData) =>
    request("/api/v1/audio/transcribe", { method: "POST", body: formData }),
};
```

Notice `user_id` is gone from every call, same as before - the backend
derives it from the token. But now so is `token` itself - `store/upload.js`
can call `api.uploadDocument(formData)` exactly like the plain pre-auth
version shown in `FRONTEND_INTEGRATION.md`, with no idea auth exists at all.

**Note:** `getToken()` is async and the token is short-lived (Clerk
auto-refreshes it behind the scenes) - that's exactly why `request()` calls
`getAuthToken()` fresh on every call rather than caching a token anywhere;
don't "optimize" this by storing the resolved token in Zustand state, it
will go stale.

## 8. Show the user's identity / sign-out

Clerk's `<UserButton />` gives you an avatar + dropdown with sign-out for
free - drop it into `TopBar.jsx` next to the existing `ThemeToggle`:

```jsx
import { UserButton } from "@clerk/react";
// ...
<UserButton afterSignOutUrl="/sign-in" />
```

## Edge cases

1. **Expired/invalid token mid-session.** If a request comes back `401`
   (session expired, revoked, etc.), don't just show a generic error -
   redirect to `/sign-in`. Consider a small wrapper around `api.js`'s
   `request()` that catches a `401` specifically and triggers
   `useAuth().signOut()` + redirect, so a stale session doesn't strand the
   user on a broken chat screen.
2. **First load flash.** Covered above via `isLoaded` - don't skip it, it's
   a real (if brief) visual bug otherwise.
3. **Google sign-in requires dashboard setup.** Works instantly in
   development (Clerk provides shared dev OAuth credentials), but going to
   production requires creating your own Google OAuth credentials in Google
   Cloud Console and adding them in the Clerk Dashboard - a one-time task
   for whoever owns the Clerk account, not something in this codebase.
4. **`VITE_` prefix is required.** Vite only exposes env vars prefixed
   `VITE_` to client code (`import.meta.env`) - `CLERK_PUBLISHABLE_KEY`
   without the prefix will silently be `undefined` in the browser, not an
   error at build time. Easy mistake, easy to lose an hour to.
5. **This frontend has no environment file checked in at all yet** (no
   `.env.example` for the frontend, unlike the backend). Add one alongside
   your `VITE_CLERK_PUBLISHABLE_KEY`/`VITE_API_BASE_URL` work so the next
   person doesn't have to reverse-engineer which env vars exist from reading
   component source.
