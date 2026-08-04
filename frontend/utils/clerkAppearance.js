import { getThemeColors } from "./Colors"

export function getClerkAppearance(theme) {
  const colors = getThemeColors(theme);

  return {
    variables: {
      colorPrimary: colors.primary,
      colorForeground: colors.text,
      colorPrimaryForeground: colors.textInverse,
      colorMutedForeground: colors.text,
      colorMuted: colors.background,
      colorBackground: colors.surface,
      colorInput: colors.background,
      colorInputForeground: colors.text,
      colorNeutral: colors.border,
      colorRing: colors.primary,
      colorBorder: colors.border,
      colorModalBackdrop: colors.overlay,
      colorDanger: colors.error,
      colorSuccess: colors.success,
      colorWarning: colors.warning,
      colorText: colors.text,
      colorTextSecondary: colors.text,
      colorTextOnPrimaryBackground: colors.textInverse,
      colorInputBackground: colors.background,
      colorInputText: colors.text,
      borderRadius: "16px",
    },

    elements: {
      rootBox: "clerk-themed-auth w-full",

      card:
        "bg-transparent shadow-none border-none text-text",

      headerTitle:
        "hidden",

      headerSubtitle:
        "hidden",

      footer:
        "hidden",

      socialButtonsBlockButton:
        "rounded-xl border-border bg-surface text-text hover:bg-background focus:ring-2 focus:ring-primary-ring",

      socialButtonsBlockButtonText:
        "font-medium text-text",

      formFieldInput:
        "rounded-xl border-border bg-background text-text caret-primary placeholder:text-textMuted focus:border-primary focus:ring-2 focus:ring-primary-ring",

      formFieldInputShowPasswordButton:
        "text-primary hover:text-primaryHover",

      formFieldInputShowPasswordIcon:
        "text-primary",

      otpCodeField:
        "text-text",

      otpCodeFieldInputs:
        "gap-2",

      otpCodeFieldInput:
        "rounded-xl border border-border bg-background text-text caret-primary shadow-none focus:border-primary focus:ring-2 focus:ring-primary-ring",

      formButtonPrimary:
        "rounded-xl bg-primary text-textInverse hover:bg-primaryHover focus:ring-2 focus:ring-primary-ring",

      dividerLine:
        "bg-border",

      dividerText:
        "text-text",

      formFieldLabel:
        "font-medium text-text",

      formFieldHintText:
        "text-text",

      footerActionText:
        "text-text",

      footerActionLink:
        "text-primary hover:text-primaryHover",

      formFieldAction:
        "text-primary hover:text-primaryHover",

      formResendCodeLink:
        "text-primary hover:text-primaryHover",

      identityPreviewText:
        "text-text",

      identityPreviewEditButton:
        "text-primary hover:text-primaryHover",
    },
  };
}
