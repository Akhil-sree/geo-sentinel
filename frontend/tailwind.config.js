/** @type {import('tailwindcss').Config} */

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],

  theme: {
    extend: {
      colors: {
        // surfaces (light, from reference)
        background: "#fbf9f1",
        surface: "#fbf9f1",
        "surface-bright": "#fbf9f1",
        "surface-container": "#f0eee6",
        "surface-container-low": "#f6f4ec",
        "surface-container-lowest": "#ffffff",
        "surface-container-high": "#eae8e0",
        "surface-variant": "#e4e3db",
        "border-muted": "#d9e2d9",
        "soft-sage": "#dce9de",

        // brand
        primary: "#04442f",
        "deep-forest": "#04442f",
        "primary-container": "#245c45",
        "primary-fixed": "#b5efd1",
        "on-primary": "#ffffff",
        "on-surface": "#1b1c17",
        "on-surface-variant": "#404943",
        outline: "#707973",
        "outline-variant": "#c0c9c2",
        secondary: "#904d00",
        "secondary-container": "#fe932c",

        // risk + status
        error: "#ba1a1a",
        "risk-low": "#245c45",
        "risk-moderate": "#d97706",
        "risk-critical": "#991b1b",
        "risk-veryhigh": "#ba1a1a",
      },

      fontFamily: {
        headline: ["'EB Garamond'", "serif"],
        body: ["'Hanken Grotesk'", "sans-serif"],
      },
    },
  },

  plugins: [],
};