import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth as useClerkAuth } from "@clerk/react";

import WelcomeView from "./WelcomeView";
import ClerkView from "./ClerkView";
import { useAuth as useLocalAuth } from "../../../store/auth";

function AuthModal({ onClose }) {
  const [view, setView] = useState("welcome");
  const { isSignedIn } = useClerkAuth();
  const closeWelcome = useLocalAuth((state) => state.closeWelcome);

  useEffect(() => {
    if (isSignedIn) {
      closeWelcome();
      onClose?.();
    }
  }, [isSignedIn, closeWelcome, onClose]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-overlay p-4 backdrop-blur-md">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0 }}
        className="w-full max-w-md overflow-hidden rounded-3xl border border-border bg-surface shadow-2xl"
      >
        <AnimatePresence mode="wait">
          {view === "welcome" && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, x: 15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -15 }}
            >
              <WelcomeView
                onSignIn={() => setView("signin")}
                onSignUp={() => setView("signup")}
                onClose={onClose}
              />
            </motion.div>
          )}

          {view === "signin" && (
            <motion.div
              key="signin"
              initial={{ opacity: 0, x: 15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -15 }}
            >
              <ClerkView
                mode="signin"
                onBack={() => setView("welcome")}
                onSwitch={() => setView("signup")}
              />
            </motion.div>
          )}

          {view === "signup" && (
            <motion.div
              key="signup"
              initial={{ opacity: 0, x: 15 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -15 }}
            >
              <ClerkView
                mode="signup"
                onBack={() => setView("welcome")}
                onSwitch={() => setView("signin")}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

export default AuthModal;
