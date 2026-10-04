import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "coverage",
      "storybook-static",
      "public",
      ".storybook",
      "src/models/api/schema.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  jsxA11y.flatConfigs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-exports": ["error", { restrictDefaultExports: { direct: true } }],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "jsx-a11y/no-noninteractive-tabindex": ["error", { roles: ["region", "tabpanel"] }],
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "vitest.setup.ts"],
    rules: { "@typescript-eslint/no-unsafe-assignment": "off" },
  },
  {
    files: ["vite.config.ts", "eslint.config.js", "**/*.stories.tsx", ".storybook/**"],
    rules: { "no-restricted-exports": "off" },
  },
  {
    files: ["eslint.config.js"],
    extends: [tseslint.configs.disableTypeChecked],
    languageOptions: { globals: globals.node },
  },
);
