import { defineConfig } from "tsup";

export default defineConfig([
  {
    entry: {
      index: "src/index.ts",
      "core/index": "src/core/index.ts",
      "react/index": "src/react/index.ts",
    },
    format: ["esm"],
    dts: true,
    sourcemap: true,
    clean: false,
    treeshake: true,
    external: ["react", "react-dom", "react/jsx-runtime"],
    outDir: "dist",
  },
  {
    entry: {
      styles: "src/styles/styles.css",
      tokens: "src/styles/tokens.css",
    },
    outDir: "dist",
    clean: false,
    loader: { ".woff2": "copy" },
    esbuildOptions(options) {
      options.assetNames = "fonts/[name]";
    },
    onSuccess: "mkdir -p dist/fonts && cp src/styles/fonts/OFL-*.txt dist/fonts/",
  },
]);
