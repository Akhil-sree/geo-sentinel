import type { Severity } from "../types/risk";

export const SEV_ORDER: Severity[] = ["LOW", "MODERATE", "HIGH", "VERY_HIGH"];

export const SEV_COLOR: Record<Severity, string> = {
  LOW: "#245c45",
  MODERATE: "#d97706",
  HIGH: "#ea580c",
  VERY_HIGH: "#ba1a1a",
};

export const SEV_FILL_OPACITY: Record<Severity, number> = {
  LOW: 0.2, MODERATE: 0.3, HIGH: 0.4, VERY_HIGH: 0.55,
};

export const SEV_LABEL: Record<Severity, string> = {
  LOW: "Low", MODERATE: "Moderate", HIGH: "High", VERY_HIGH: "Very High",
};

export const SEV_DESCRIPTION: Record<Severity, string> = {
  LOW: "Conditions stable. No significant landslide indicators detected.",
  MODERATE: "Elevated risk detected. Monitor conditions and stay informed.",
  HIGH: "High risk of slope instability. Avoid steep terrain and road cuts during rainfall.",
  VERY_HIGH: "Critical risk — multiple indicators suggest imminent instability. Follow local authority guidance.",
};

export const SEV_ACTION: Record<Severity, string> = {
  LOW: "Continue routine monitoring.",
  MODERATE: "Issue public advisory. Prepare response teams.",
  HIGH: "Deploy advisory to at-risk populations. Activate response protocols.",
  VERY_HIGH: "Immediate coordination with DDMA. Activate emergency response.",
};

export const SEV_ICON: Record<Severity, string> = {
  LOW: "\u2713",
  MODERATE: "\u26A0",
  HIGH: "\u25B2",
  VERY_HIGH: "\u26D4",
};

export const sevIndex = (s: Severity) => SEV_ORDER.indexOf(s);
export const atLeast = (s: Severity, min: Severity) => sevIndex(s) >= sevIndex(min);
export const isAlertEligible = (s: Severity) => atLeast(s, "HIGH");
