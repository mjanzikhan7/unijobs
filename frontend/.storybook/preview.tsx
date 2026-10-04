import type { Decorator, Preview } from "@storybook/react-vite";
import { useEffect } from "react";
import { ThemeProvider } from "@mui/material/styles";

import "@fontsource-variable/inter";
import "@fontsource-variable/space-grotesk";
import "../src/styles/tokens.css";
import "../src/styles/tailwind.css";
import "../src/styles/base.css";

import { muiTheme } from "../src/styles/muiTheme";

const withTheme: Decorator = (Story, context) => {
  const theme = context.globals.theme as "light" | "dark";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return (
    <ThemeProvider theme={muiTheme}>
      <Story />
    </ThemeProvider>
  );
};

const preview: Preview = {
  decorators: [withTheme],
  globalTypes: {
    theme: {
      description: "Theme, driven by the same [data-theme] attribute the real app uses",
      toolbar: {
        title: "Theme",
        icon: "circlehollow",
        items: [
          { value: "light", title: "Light", icon: "sun" },
          { value: "dark", title: "Dark", icon: "moon" },
        ],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: { theme: "light" },
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      test: "error",
    },
  },
};

export default preview;
