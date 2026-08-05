import { useEffect, useLayoutEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { useAuth as useClerkAuth } from "@clerk/react";

import { useTheme } from "../store/theme";
import { useAuth as useLocalAuth } from "../store/auth";
import { useDocuments } from "../store/documents";
import { applyThemeColors } from "../utils/Colors";

import Chat from "./Pages/Chat";
import NotFound from "./Pages/NotFound";

import AuthModal from "./components/auth/AuthModal";
import AuthBridge from "./components/auth/AuthBridge";
import ToastContainer from "./components/ui/ToastContainer";

function App() {
  const theme = useTheme((state) => state.theme);
  const welcomeVisible = useLocalAuth((state) => state.welcomeVisible);
  const welcomeDismissed = useLocalAuth((state) => state.welcomeDismissed);
  const openWelcome = useLocalAuth((state) => state.openWelcome);
  const closeWelcome = useLocalAuth((state) => state.closeWelcome);
  const { isLoaded, isSignedIn } = useClerkAuth();
  const fetchDocuments = useDocuments((s) => s.fetchDocuments);

  useLayoutEffect(() => {
    applyThemeColors(theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      closeWelcome();
      fetchDocuments();
    }
  }, [isLoaded, isSignedIn, closeWelcome, fetchDocuments]);

  useEffect(() => {
    if (isLoaded && !isSignedIn && !welcomeDismissed) {
      openWelcome();
    }
  }, [isLoaded, isSignedIn, welcomeDismissed, openWelcome]);

  if (!isLoaded) return null;

  return (
    <>
      <ToastContainer />

      {(!isSignedIn && welcomeVisible) && (
        <AuthModal
          onClose={closeWelcome}
        />
      )}

      <BrowserRouter>
        <AuthBridge />
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
