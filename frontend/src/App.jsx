import { useEffect, useLayoutEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { useAuth as useClerkAuth } from "@clerk/react";

import { useTheme } from "../store/theme";
import { useAuth as useLocalAuth } from "../store/auth";
import { useDocuments } from "../store/documents";
import { applyThemeColors } from "../utils/Colors";

import Chat from "./Pages/Chat";
import NotFound from "./Pages/NotFound";
import Settings from "./Pages/Settings";

import AuthModal from "./components/auth/AuthModal";
import AuthBridge from "./components/auth/AuthBridge";
import ToastContainer from "./components/ui/ToastContainer";
import UpgradeModal from "./components/ui/UpgradeModal";
import RoleSelectionModal from "./components/ui/RoleSelectionModal";
import BillingModal from "./components/ui/BillingModal";
import { useProfile } from "../store/profile";
import { useUI } from "../store/ui";

function App() {
  const theme = useTheme((state) => state.theme);
  const welcomeVisible = useLocalAuth((state) => state.welcomeVisible);
  const welcomeDismissed = useLocalAuth((state) => state.welcomeDismissed);
  const openWelcome = useLocalAuth((state) => state.openWelcome);
  const closeWelcome = useLocalAuth((state) => state.closeWelcome);
  const { isLoaded, isSignedIn } = useClerkAuth();
  const fetchDocuments = useDocuments((s) => s.fetchDocuments);
  const { profile, fetchProfile, loading: profileLoading } = useProfile();
  const { openRoleSelectionModal, roleSelectionModalOpen, closeRoleSelectionModal, openBillingModal } = useUI();

  useLayoutEffect(() => {
    applyThemeColors(theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      closeWelcome();
      fetchDocuments();
      // fetch user profile on sign-in so role and chambers are available
      fetchProfile().catch(() => {});
    }
  }, [isLoaded, isSignedIn, closeWelcome, fetchDocuments, fetchProfile]);

  // Show role selection modal if profile is loaded but role is not set
  useEffect(() => {
    if (isLoaded && isSignedIn && profile && !profileLoading) {
      // Check if role is empty
      const hasRole = profile.role && profile.role.trim() !== '';
      if (!hasRole) {
        openRoleSelectionModal();
      }
    }
  }, [isLoaded, isSignedIn, profile, profileLoading, openRoleSelectionModal]);

  // Show billing modal after role selection is closed (meaning role was saved)
  useEffect(() => {
    if (!roleSelectionModalOpen && profile && profile.role && profile.role.trim() !== '') {
      // Role was just saved, now show billing
      openBillingModal();
    }
  }, [roleSelectionModalOpen, profile, openBillingModal]);

  useEffect(() => {
    if (isLoaded && !isSignedIn && !welcomeDismissed) {
      openWelcome();
    }
  }, [isLoaded, isSignedIn, welcomeDismissed, openWelcome]);

  if (!isLoaded) return null;

  return (
    <>
      <ToastContainer />
      <UpgradeModal />
      <RoleSelectionModal />
      <BillingModal />

      {(!isSignedIn && welcomeVisible) && (
        <AuthModal
          onClose={closeWelcome}
        />
      )}

      <BrowserRouter>
        <AuthBridge />
        
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
