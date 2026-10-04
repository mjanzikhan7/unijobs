import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@fontsource-variable/inter";
import "@fontsource-variable/space-grotesk";
import "@unijobs/a11y/tokens.css";
import "./styles/tokens.css";
import "./styles/tailwind.css";
import "./styles/base.css";
import "@unijobs/a11y/styles.css";

import { App } from "./App";

const container = document.getElementById("root");
if (!container) throw new Error("No #root element to mount into");

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
