import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ClerkProvider } from "@clerk/react";
import { applyThemeColors } from "../utils/Colors";

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
