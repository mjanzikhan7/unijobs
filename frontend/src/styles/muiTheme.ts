import { createTheme } from "@mui/material/styles";

import { palette, radius, typography } from "./tokens";

function schemePalette(mode: "light" | "dark") {
  const tokens = palette[mode];
  return {
    primary: {
      main: tokens.brand,
      dark: tokens.brandActive,
      contrastText: tokens.textInverse,
    },
    secondary: { main: tokens.cta, contrastText: tokens.textInverse },
    error: { main: tokens.dangerText },
    warning: { main: tokens.warningText },
    info: { main: tokens.infoText },
    success: { main: tokens.successText },
    background: { default: tokens.bg, paper: tokens.surface },
    text: {
      primary: tokens.textPrimary,
      secondary: tokens.textSecondary,
      disabled: tokens.textMuted,
    },
    divider: tokens.borderSubtle,
  };
}

export const muiTheme = createTheme({
  cssVariables: { colorSchemeSelector: "[data-theme=%s]" },
  colorSchemes: {
    light: { palette: schemePalette("light") },
    dark: { palette: schemePalette("dark") },
  },
  shape: { borderRadius: radius.md },
  typography: { fontFamily: `"${typography.fontSans}", system-ui, sans-serif` },
});
