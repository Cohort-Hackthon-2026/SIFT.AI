import { useEffect, useLayoutEffect, useRef } from "react";
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
import ChamberSelectionModal from "./components/ui/ChamberSelectionModal";
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
  const { openRoleSelectionModal, roleSelectionModalOpen, openChamberSelectionModal, chamberSelectionModalOpen, openBillingModal } = useUI();
  const roleSelectionPromptedRef = useRef(false);
  const chamberSelectionPromptedRef = useRef(false);

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

  // Show role selection modal once per sign-in when the user does not have a role
  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      roleSelectionPromptedRef.current = false;
      return;
    }

    if (!profile || profileLoading) {
      return;
    }

    const hasRole = profile.role && profile.role.trim() !== '';
    if (!hasRole && !roleSelectionPromptedRef.current && !roleSelectionModalOpen) {
      roleSelectionPromptedRef.current = true;
      openRoleSelectionModal();
    }
  }, [isLoaded, isSignedIn, profile, profileLoading, roleSelectionModalOpen, openRoleSelectionModal]);

  // Show chamber selection modal once per sign-in when the user has role but no chambers
  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      chamberSelectionPromptedRef.current = false;
      return;
    }

    if (!profile || profileLoading || roleSelectionModalOpen) {
      return;
    }

    const hasRole = profile.role && profile.role.trim() !== '';
    const hasChambers = Boolean(profile.chambers_id);

    if (hasRole && !hasChambers && !chamberSelectionPromptedRef.current && !chamberSelectionModalOpen) {
      chamberSelectionPromptedRef.current = true;
      openChamberSelectionModal();
    }
  }, [isLoaded, isSignedIn, profile, profileLoading, roleSelectionModalOpen, chamberSelectionModalOpen, openChamberSelectionModal]);

  // Show billing modal after both role and chambers are set
  useEffect(() => {
    if (!roleSelectionModalOpen && !chamberSelectionModalOpen && profile) {
      const hasRole = profile.role && profile.role.trim() !== '';
      const hasChambers = Boolean(profile.chambers_id);
      if (hasRole && hasChambers) {
        openBillingModal();
      }
    }
  }, [roleSelectionModalOpen, chamberSelectionModalOpen, profile, openBillingModal]);

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
      <ChamberSelectionModal />
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
