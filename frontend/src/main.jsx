import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ClerkProvider } from "@clerk/react";
import { applyThemeColors } from "../utils/Colors";
import { useUI } from "../store/ui";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing VITE_CLERK_PUBLISHABLE_KEY - check frontend/.env");
}

function getStoredTheme() {
  try {
    return JSON.parse(localStorage.getItem("theme"))?.state?.theme || "light";
  } catch {
    return "light";
  }
}

const initialTheme = getStoredTheme();
applyThemeColors(initialTheme);
document.documentElement.classList.toggle("dark", initialTheme === "dark");

createRoot(document.getElementById('root')).render(
  <StrictMode>
   <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
      <App />
    </ClerkProvider>
  </StrictMode>,
)

// expose a global hook the API client can call when a 402 upgrade envelope is returned
try {
  // eslint-disable-next-line no-undef
  window.__sift_open_upgrade = (detail) => {
    try {
      useUI.getState().openUpgradeModal(detail);
    } catch (e) {
      // noop
    }
  };
} catch (e) {
  // noop in non-browser environments
}
