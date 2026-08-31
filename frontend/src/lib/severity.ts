import type { Severity } from "../types/risk";

export const SEV_ORDER: Severity[] = ["LOW", "MODERATE", "HIGH", "VERY_HIGH"];

export const SEV_COLOR: Record<Severity, string> = {
  LOW: "#245c45",        // deep green
  MODERATE: "#d97706",   // amber
  HIGH: "#ea580c",       // orange
  VERY_HIGH: "#ba1a1a",  // critical red
};

export const SEV_FILL_OPACITY: Record<Severity, number> = {
  LOW: 0.2, MODERATE: 0.3, HIGH: 0.4, VERY_HIGH: 0.55,
};

export const SEV_LABEL: Record<Severity, string> = {
  LOW: "Low", MODERATE: "Moderate", HIGH: "High", VERY_HIGH: "Very High",
};

export const sevIndex = (s: Severity) => SEV_ORDER.indexOf(s);
export const atLeast = (s: Severity, min: Severity) => sevIndex(s) >= sevIndex(min);
export const isAlertEligible = (s: Severity) => atLeast(s, "HIGH");
