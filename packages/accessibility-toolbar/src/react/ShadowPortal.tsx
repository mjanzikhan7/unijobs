import { useLayoutEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { ReactNode } from "react";

import { TOOLBAR_HOST_ID } from "../core/constants";

export interface ShadowPortalProps {
  children: ReactNode;
  css: string;
  hostId?: string;
}

export function ShadowPortal({ children, css, hostId = TOOLBAR_HOST_ID }: ShadowPortalProps) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    let host = document.getElementById(hostId) as HTMLDivElement | null;
    let createdHost = false;
    if (!host) {
      host = document.createElement("div");
      host.id = hostId;
      document.body.appendChild(host);
      createdHost = true;
    }

    const shadow = host.shadowRoot ?? host.attachShadow({ mode: "open" });
    let mountPoint = shadow.getElementById("mount") as HTMLDivElement | null;
    if (!mountPoint) {
      mountPoint = document.createElement("div");
      mountPoint.id = "mount";
      shadow.appendChild(mountPoint);
    }

    const supportsAdoptedStyleSheets =
      typeof CSSStyleSheet !== "undefined" && "replaceSync" in CSSStyleSheet.prototype;
    if (supportsAdoptedStyleSheets) {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(css);
      shadow.adoptedStyleSheets = [sheet];
    } else {
      let styleTag = shadow.querySelector<HTMLStyleElement>("style");
      if (!styleTag) {
        styleTag = document.createElement("style");
        shadow.insertBefore(styleTag, shadow.firstChild);
      }
      styleTag.textContent = css;
    }

    setContainer(mountPoint);

    return () => {
      if (createdHost) host?.remove();
    };
  }, [css, hostId]);

  if (!container) return null;
  return createPortal(children, container);
}
