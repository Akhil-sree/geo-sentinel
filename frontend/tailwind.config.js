/** @type {import('tailwindcss').Config} */

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],

  theme: {
    extend: {
      colors: {
        /* ── Brand: Deep Forest ── */
        "brand-green": "#075240",
        "forest-dark": "#0B3D32",
        "olive": "#6B7A32",
        "sand": "#E8DDC7",
        "navy": { DEFAULT: "#0B3D32", light: "#0D4A3A" },
        "forest": {
          DEFAULT: "#075240",
          50: "#ECFDF5",
          100: "#D1FAE5",
          200: "#A7F3D0",
          300: "#6EE7B7",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
          800: "#065F46",
          900: "#075240",
          950: "#022C22",
        },

        /* ── Surfaces (Earthmorphism + Geomorphism) ── */
        "gs-bg": "#F4F1EB",
        "gs-surface": "#FDFCFA",
        "gs-surface-soft": "#EDE9E0",
        "gs-card": "#FDFCFA",
        "gs-border": "#D6D0C4",
        "gs-text": "#2A332D",
        "gs-text-secondary": "#5F6B62",

        /* ── Terrain Layers (Elevation-based) ── */
        "terrain-base": "#F4F1EB",
        "terrain-low": "#EDE9E0",
        "terrain-mid": "#E2DACE",
        "terrain-high": "#D6D0C4",
        "terrain-ridge": "#C4BCB0",
        "terrain-peak": "#B0A898",
        "terrain-summit": "#9A9286",

        /* ── Geomorphic Accents ── */
        "geo-moss": "#4A7C59",
        "geo-clay": "#B5724A",
        "geo-slate": "#5D6B5E",
        "geo-mist": "#C8D6D0",
        "geo-amber": "#C8964E",

        /* ── Risk spectrum ── */
        "risk-low": "#2563EB",
        "risk-moderate": "#C8964E",
        "risk-high": "#C25D3A",
        "risk-critical": "#A63238",

        /* ── Semantic aliases ── */
        "risk-stable": "#2563EB",
        "risk-stressed": "#C8964E",
        "risk-degrading": "#C25D3A",
        background: "#F4F1EB",
        surface: "#FDFCFA",
        primary: "#075240",
        "deep-forest": "#075240",
        on: { primary: "#FDFCFA", surface: "#2A332D" },
        error: "#A63238",
        outline: "#5F6B62",
        "outline-variant": "#D6D0C4",
        secondary: "#0B3D32",
      },

      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },

      borderRadius: {
        card: "16px",
        "card-lg": "24px",
        "organic-sm": "12px 16px 14px 18px",
        "organic-md": "18px 24px 20px 28px",
        "organic-lg": "24px 32px 28px 36px",
        "terrain": "8px 12px 16px 10px",
      },

      boxShadow: {
        /* ── Terrain elevation shadows ── */
        "terrain-1": "0 1px 3px rgba(42, 51, 45, 0.04), 0 2px 6px rgba(42, 51, 45, 0.02)",
        "terrain-2": "0 2px 8px rgba(42, 51, 45, 0.06), 0 4px 12px rgba(42, 51, 45, 0.03)",
        "terrain-3": "0 4px 16px rgba(42, 51, 45, 0.08), 0 8px 24px rgba(42, 51, 45, 0.04)",
        "terrain-4": "0 8px 32px rgba(42, 51, 45, 0.10), 0 16px 48px rgba(42, 51, 45, 0.05)",

        /* ── Geomorphic floating shadows ── */
        "geo-float": "0 4px 20px rgba(42, 51, 45, 0.08), 0 1px 4px rgba(42, 51, 45, 0.04), inset 0 1px 0 rgba(255,255,255,0.6)",
        "geo-float-lg": "0 8px 40px rgba(42, 51, 45, 0.12), 0 2px 8px rgba(42, 51, 45, 0.06), inset 0 1px 0 rgba(255,255,255,0.5)",
        "geo-inset": "inset 0 2px 4px rgba(42, 51, 45, 0.06), inset 0 1px 2px rgba(42, 51, 45, 0.04)",

        /* ── Glassmorphism with earth depth ── */
        "glass": "0 2px 16px rgba(42, 51, 45, 0.06), 0 1px 4px rgba(42, 51, 45, 0.03), inset 0 1px 0 rgba(255,255,255,0.5)",
        "glass-lg": "0 4px 28px rgba(42, 51, 45, 0.08), 0 2px 8px rgba(42, 51, 45, 0.04), inset 0 1px 0 rgba(255,255,255,0.4)",

        /* ── Card shadows (elevation) ── */
        "card": "0 2px 8px rgba(42, 51, 45, 0.05), 0 1px 3px rgba(42, 51, 45, 0.03)",
        "card-hover": "0 6px 24px rgba(42, 51, 45, 0.10), 0 2px 8px rgba(42, 51, 45, 0.05)",
        "card-elevated": "0 4px 16px rgba(42, 51, 45, 0.08), 0 2px 6px rgba(42, 51, 45, 0.04)",
      },

      /* ── Geomorphic backdrop effects ── */
      backdropBlur: {
        glass: "12px",
        "glass-lg": "18px",
        "glass-sm": "8px",
      },

      /* ── Geomorphic gradients ── */
      backgroundImage: {
        /* Terrain elevation gradients */
        "terrain-gradient": "linear-gradient(165deg, #F4F1EB 0%, #EDE9E0 25%, #E2DACE 50%, #D6D0C4 75%, #C4BCB0 100%)",
        "terrain-vertical": "linear-gradient(180deg, #F4F1EB 0%, #EDE9E0 30%, #E2DACE 60%, #D6D0C4 100%)",
        "terrain-radial": "radial-gradient(ellipse at 30% 20%, #FDFCFA 0%, #EDE9E0 40%, #E2DACE 70%, #D6D0C4 100%)",

        /* Topographic contour-inspired */
        "contour-subtle": "repeating-conic-gradient(from 0deg at 50% 50%, rgba(7, 82, 64, 0.01) 0deg, transparent 3deg, transparent 30deg)",

        /* Glass with earth undertone */
        "glass-gradient": "linear-gradient(135deg, rgba(253,252,250,0.92) 0%, rgba(237,233,224,0.88) 50%, rgba(226,218,206,0.85) 100%)",
        "glass-warm": "linear-gradient(145deg, rgba(253,252,250,0.95) 0%, rgba(244,241,235,0.90) 100%)",

        /* Organic flow backgrounds */
        "flow-forest": "linear-gradient(135deg, rgba(7, 82, 64, 0.03) 0%, rgba(74, 124, 89, 0.02) 50%, transparent 100%)",
        "flow-warm": "linear-gradient(135deg, rgba(181, 114, 74, 0.03) 0%, rgba(200, 150, 78, 0.02) 50%, transparent 100%)",
      },

      /* ── Organic animation timing ── */
      animation: {
        "terrain-breathe": "terrain-breathe 6s ease-in-out infinite",
        "geo-float": "geo-float 3s ease-in-out infinite",
        "contour-shift": "contour-shift 12s linear infinite",
        "elevation-rise": "elevation-rise 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)",
      },

      keyframes: {
        "terrain-breathe": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.8" },
          "50%": { transform: "scale(1.01)", opacity: "1" },
        },
        "geo-float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-3px)" },
        },
        "contour-shift": {
          "0%": { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "100% 100%" },
        },
        "elevation-rise": {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },

  plugins: [],
};
