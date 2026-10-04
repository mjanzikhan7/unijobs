export const DALTONIZE_FILTER_IDS = {
  protanopia: "unijobs-a11y-daltonize-protanopia",
  deuteranopia: "unijobs-a11y-daltonize-deuteranopia",
  tritanopia: "unijobs-a11y-daltonize-tritanopia",
} as const;

const MATRICES: Record<keyof typeof DALTONIZE_FILTER_IDS, string> = {
  protanopia: "0.856 0.182 -0.038 0 0  0.029 0.905 0.066 0 0  -0.002 -0.001 1.003 0 0  0 0 0 1 0",
  deuteranopia: "0.8 0.258 -0.058 0 0  0.19 0.83 -0.02 0 0  0.017 0.017 0.966 0 0  0 0 0 1 0",
  tritanopia: "0.885 0.098 0.017 0 0  0.026 0.908 0.065 0 0  0.028 0.972 -0.001 0 0  0 0 0 1 0",
};

const CONTAINER_ID = "unijobs-a11y-daltonize-defs";

export function ensureDaltonizeFilters(mountPoint: HTMLElement): void {
  if (mountPoint.ownerDocument.getElementById(CONTAINER_ID)) return;

  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("id", CONTAINER_ID);
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.style.position = "absolute";
  svg.style.width = "0";
  svg.style.height = "0";
  svg.style.overflow = "hidden";

  const defs = document.createElementNS(svgNs, "defs");
  for (const key of Object.keys(MATRICES) as Array<keyof typeof MATRICES>) {
    const filter = document.createElementNS(svgNs, "filter");
    filter.setAttribute("id", DALTONIZE_FILTER_IDS[key]);
    filter.setAttribute("color-interpolation-filters", "sRGB");
    const matrix = document.createElementNS(svgNs, "feColorMatrix");
    matrix.setAttribute("type", "matrix");
    matrix.setAttribute("values", MATRICES[key]);
    filter.appendChild(matrix);
    defs.appendChild(filter);
  }
  svg.appendChild(defs);
  mountPoint.appendChild(svg);
}

export function removeDaltonizeFilters(mountPoint: HTMLElement): void {
  mountPoint.ownerDocument.getElementById(CONTAINER_ID)?.remove();
}
