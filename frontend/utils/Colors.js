export const Colors = {
  light: {
    background: "#F4F7FB",
    surface: "#FFFFFF",

    primary: "#3B5BDB",
    primaryHover: "#2F4FC7",
    primaryRing: "rgba(59,91,219,.24)",
    accent: "#14B8A6",

    text: "#182230",
    textMuted: "#667085",
    textInverse: "#FFFFFF",

    border: "#D9E2EC",
    overlay: "rgba(8,17,32,.5)",

    citation: {
      bg: "#EFF4FF",
      border: "#C7D7FE",
      text: "#2F4FC7",
    },

    error: "#EF4444",
    success: "#22C55E",
    warning: "#F59E0B",
  },

  dark: {
    background: "#0B1220",
    surface: "#131D2F",

    primary: "#5B8CFF",
    primaryHover: "#7AA3FF",
    primaryRing: "rgba(91,140,255,.32)",
    accent: "#2DD4BF",

    text: "#F8FAFC",
    textMuted: "#A8B3C7",
    textInverse: "#081120",

    border: "#22314B",
    overlay: "rgba(0,0,0,.62)",

    citation: {
      bg: "rgba(91,140,255,.15)",
      border: "rgba(122,163,255,.3)",
      text: "#93C5FD",
    },

    error: "#F87171",
    success: "#4ADE80",
    warning: "#FBBF24",
  },
}

export function getThemeColors(theme) {
  return Colors[theme] || Colors.light;
}

export function getColorCssVariables(theme) {
  const colors = getThemeColors(theme);

  return {
    "--background": colors.background,
    "--surface": colors.surface,
    "--primary": colors.primary,
    "--primary-hover": colors.primaryHover,
    "--primary-ring": colors.primaryRing,
    "--accent": colors.accent,
    "--text": colors.text,
    "--text-muted": colors.textMuted,
    "--text-inverse": colors.textInverse,
    "--border": colors.border,
    "--overlay": colors.overlay,
    "--citation-bg": colors.citation.bg,
    "--citation-border": colors.citation.border,
    "--citation-text": colors.citation.text,
    "--error": colors.error,
    "--success": colors.success,
    "--warning": colors.warning,
  };
}

export function applyThemeColors(theme, root) {
  const target = root || globalThis.document?.documentElement;

  if (!target) return;

  Object.entries(getColorCssVariables(theme)).forEach(([name, value]) => {
    target.style.setProperty(name, value);
  });

  target.dataset.theme = theme === "dark" ? "dark" : "light";
  target.style.colorScheme = theme === "dark" ? "dark" : "light";
}
