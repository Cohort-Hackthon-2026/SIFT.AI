import { ArrowLeft } from "lucide-react";
import { SignIn, SignUp } from "@clerk/react";

import { useTheme } from "../../../store/theme";
import { getColorCssVariables, getThemeColors } from "../../../utils/Colors";
import { getClerkAppearance } from "../../../utils/clerkAppearance";

function ClerkView({
  mode,
  onBack,
  onSwitch,
}) {
  const theme = useTheme((state) => state.theme);
  const colors = getThemeColors(theme);

  const isSignIn = mode === "signin";
  const authThemeStyle = {
    ...getColorCssVariables(theme),
    color: colors.text,
  };

  return (
    <div
      className="auth-theme-scope flex flex-col"
      style={authThemeStyle}
    >

      <div className="flex items-center justify-between border-b border-border p-6">

        <button
          onClick={onBack}
          className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition hover:bg-background"
          style={{ color: colors.primary }}
        >
          <ArrowLeft size={18} />
          Back
        </button>

        <h2
          className="text-lg font-semibold"
          style={{ color: colors.text }}
        >
          {isSignIn ? "Sign In" : "Create Account"}
        </h2>

        <div className="w-16" />

      </div>

      <div className="p-6">

        {isSignIn ? (
          <SignIn
            routing="virtual"
            appearance={getClerkAppearance(theme)}
          />
        ) : (
          <SignUp
            routing="virtual"
            appearance={getClerkAppearance(theme)}
          />
        )}

        <div
          className="mt-6 text-center text-sm"
          style={{ color: colors.text }}
        >

          {isSignIn
            ? "Don't have an account?"
            : "Already have an account?"}

          <button
            onClick={onSwitch}
            className="ml-2 font-medium hover:underline"
            style={{ color: colors.primary }}
          >
            {isSignIn ? "Create one" : "Sign in"}
          </button>

        </div>

      </div>

    </div>
  );
}

export default ClerkView;
