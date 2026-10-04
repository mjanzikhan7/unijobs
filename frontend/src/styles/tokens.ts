export const palette = {
  light: {
    bg: "#F6F8FC",
    surface: "#FFFFFF",
    surfaceRaised: "#FFFFFF",
    surfaceSunken: "#EEF1F8",
    overlay: "rgba(14,19,34,0.55)",
    borderSubtle: "#E3E8F2",
    borderStrong: "#838CA2",
    textPrimary: "#0E1322",
    textSecondary: "#48526A",
    textMuted: "#616A84",
    textInverse: "#FFFFFF",
    brand: "#4E37E5",
    brandHover: "#4229C4",
    brandActive: "#3720A3",
    brandSubtleBg: "#EDEAFE",
    accent: "#0A6C8C",
    accentVivid: "#06B6D4",
    cta: "#B0126B",
    ctaHover: "#97095A",
    ctaActive: "#7E0349",
    ctaSubtleBg: "#FCE7F3",
    focusRing: "#4E37E5",
    successText: "#0A6E3D", successBg: "#E4F6EC",
    warningText: "#7A4A00", warningBg: "#FCF0D8",
    dangerText: "#A81F26", dangerBg: "#FCE7E7",
    infoText: "#0B5CA8", infoBg: "#E3F0FD",
    neutralText: "#3F4757", neutralBg: "#EDEFF4",
    unknownText: "#7228BE", unknownBg: "#F3E8FD",
    workplaceRemoteText: "#0A6C8C", workplaceRemoteBg: "#E0F4FA",
    workplaceHybridText: "#0B6E62", workplaceHybridBg: "#DDF4F0",
    workplaceOnsiteText: "#3F4757", workplaceOnsiteBg: "#EDEFF4",
    matchLowText: "#3F4757", matchLowBg: "#EDEFF4",
    matchMediumText: "#7A4A00", matchMediumBg: "#FCF0D8",
    matchHighText: "#0A6E3D", matchHighBg: "#E4F6EC",
  },
  dark: {
    bg: "#0B0F1A",
    surface: "#141A28",
    surfaceRaised: "#1C2334",
    surfaceSunken: "#080B14",
    overlay: "rgba(0,0,0,0.66)",
    borderSubtle: "#242D40",
    borderStrong: "#5F6D8A",
    textPrimary: "#E8ECF5",
    textSecondary: "#A7B2C6",
    textMuted: "#8B96AC",
    textInverse: "#0B0F1A",
    brand: "#8B7BFF",
    brandHover: "#A296FF",
    brandActive: "#7666F2",
    brandSubtleBg: "#221E3F",
    accent: "#35C9EA",
    accentVivid: "#22D3EE",
    cta: "#FF6FB5",
    ctaHover: "#FF8CC5",
    ctaActive: "#EE5AA2",
    ctaSubtleBg: "#3A1730",
    focusRing: "#A296FF",
    successText: "#6EE7A8", successBg: "#0E2F1E",
    warningText: "#F5CE7A", warningBg: "#33260C",
    dangerText: "#FCA5A8", dangerBg: "#3A1618",
    infoText: "#8CC5F5", infoBg: "#10263D",
    neutralText: "#B4BECE", neutralBg: "#232B3B",
    unknownText: "#D3A6F5", unknownBg: "#2C1B3D",
    workplaceRemoteText: "#6EDBF5", workplaceRemoteBg: "#0C2A33",
    workplaceHybridText: "#5FDBC8", workplaceHybridBg: "#0C2E2A",
    workplaceOnsiteText: "#B4BECE", workplaceOnsiteBg: "#232B3B",
    matchLowText: "#B4BECE", matchLowBg: "#232B3B",
    matchMediumText: "#F5CE7A", matchMediumBg: "#33260C",
    matchHighText: "#6EE7A8", matchHighBg: "#0E2F1E",
  },
} as const;

export const applicationStatusColours = {
  light: {
    FOUND:        { text: "#3F4757", bg: "#EDEFF4" },
    READY:        { text: "#0B6E62", bg: "#DDF4F0" },
    APPLIED:      { text: "#1250B0", bg: "#E2EEFD" },
    ACKNOWLEDGED: { text: "#4338CA", bg: "#E9E8FC" },
    INTERVIEW:    { text: "#7228BE", bg: "#F3E8FD" },
    OFFER:        { text: "#0A6E3D", bg: "#E4F6EC" },
    REJECTED:     { text: "#A81F26", bg: "#FCE7E7" },
    GHOSTED:      { text: "#7A4A00", bg: "#FCF0D8" },
  },
  dark: {
    FOUND:        { text: "#B4BECE", bg: "#232B3B" },
    READY:        { text: "#5FDBC8", bg: "#0C2E2A" },
    APPLIED:      { text: "#8CC5F5", bg: "#10263D" },
    ACKNOWLEDGED: { text: "#ABA2FF", bg: "#221E3F" },
    INTERVIEW:    { text: "#D3A6F5", bg: "#2C1B3D" },
    OFFER:        { text: "#6EE7A8", bg: "#0E2F1E" },
    REJECTED:     { text: "#FCA5A8", bg: "#3A1618" },
    GHOSTED:      { text: "#F5CE7A", bg: "#33260C" },
  },
} as const;

export const matchBands = [
  { min: 70, band: "high" },
  { min: 45, band: "medium" },
  { min: 0, band: "low" },
] as const;

export const space = {
  1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32,
  10: 40, 12: 48, 16: 64, 20: 80, 24: 96, 32: 128,
} as const;

export const radius = {
  xs: 4, sm: 6, md: 10, lg: 14, xl: 20, "2xl": 28, full: 9999,
} as const;

export const borderWidth = { hairline: 1, emphasis: 2, focus: 3 } as const;

export const zIndex = {
  base: 0, raised: 10, sticky: 100, drawer: 200, overlay: 300, modal: 400, toast: 500, tooltip: 600,
} as const;

export const containers = {
  form: 440, prose: 720, narrow: 960, content: 1280, wide: 1600,
} as const;

export const shadow = {
  light: {
    xs: "0 1px 2px rgb(14 19 34 / 6%)",
    sm: "0 1px 2px rgb(14 19 34 / 6%), 0 1px 1px rgb(14 19 34 / 4%)",
    md: "0 6px 16px rgb(14 19 34 / 8%), 0 2px 6px rgb(14 19 34 / 6%)",
    lg: "0 16px 40px rgb(14 19 34 / 14%)",
    xl: "0 28px 64px rgb(14 19 34 / 18%)",
    focus: "0 0 0 3px rgb(78 55 229 / 28%)",
  },
  dark: {
    xs: "0 1px 2px rgb(0 0 0 / 40%)",
    sm: "0 1px 2px rgb(0 0 0 / 40%), 0 1px 1px rgb(0 0 0 / 28%)",
    md: "0 6px 16px rgb(0 0 0 / 46%), 0 2px 6px rgb(0 0 0 / 34%)",
    lg: "0 16px 40px rgb(0 0 0 / 56%)",
    xl: "0 28px 64px rgb(0 0 0 / 64%)",
    focus: "0 0 0 3px rgb(162 150 255 / 34%)",
  },
} as const;

export const typography = {
  fontDisplay: "Space Grotesk",
  fontSans: "Inter",
  scale: {
    "display-2xl": { size: 60, lineHeight: 1.05, tracking: -0.03, weight: 700, family: "display" },
    "display-xl":  { size: 48, lineHeight: 1.08, tracking: -0.025, weight: 700, family: "display" },
    "display-lg":  { size: 36, lineHeight: 1.15, tracking: -0.02, weight: 700, family: "display" },
    "heading-xl":  { size: 30, lineHeight: 1.20, tracking: -0.015, weight: 500, family: "display" },
    "heading-lg":  { size: 24, lineHeight: 1.25, tracking: -0.01, weight: 600, family: "sans" },
    "heading-md":  { size: 20, lineHeight: 1.30, tracking: -0.005, weight: 600, family: "sans" },
    "heading-sm":  { size: 17, lineHeight: 1.35, tracking: 0, weight: 600, family: "sans" },
    "body-lg":     { size: 18, lineHeight: 1.60, tracking: 0, weight: 400, family: "sans" },
    body:          { size: 16, lineHeight: 1.55, tracking: 0, weight: 400, family: "sans" },
    "body-sm":     { size: 14, lineHeight: 1.50, tracking: 0, weight: 400, family: "sans" },
    caption:       { size: 13, lineHeight: 1.45, tracking: 0, weight: 500, family: "sans" },
    micro:         { size: 12, lineHeight: 1.40, tracking: 0.005, weight: 600, family: "sans" },
    overline:      { size: 11, lineHeight: 1.30, tracking: 0.06, weight: 600, family: "sans" },
  },
} as const;

export const motion = {
  durationFast: 120,
  durationBase: 200,
  durationSlow: 360,
  easeOut: [0.16, 1, 0.3, 1],
  easeInOut: [0.65, 0, 0.35, 1],
} as const;

export const breakpoints = { sm: 640, md: 768, lg: 1024, xl: 1280, "2xl": 1536 } as const;

export type ThemeMode = "light" | "dark";
