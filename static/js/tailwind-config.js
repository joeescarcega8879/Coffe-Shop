/* ============================================================
   The Hearth Roastery — Tailwind theme configuration
   IMPORTANT: must be loaded BEFORE the Tailwind CDN script.
   Shared by: home.html, menu.html, detail.html, contact.html
   ============================================================ */
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "tertiary-fixed-dim": "#fbb981",
        "surface-container-low": "#f8f3eb",
        "secondary-fixed": "#ffdbcf",
        "surface": "#fef9f1",
        "primary-fixed-dim": "#e3beb8",
        "on-secondary-fixed-variant": "#5e3f35",
        "on-secondary": "#ffffff",
        "on-surface": "#1d1c17",
        "on-error": "#ffffff",
        "on-primary-fixed-variant": "#5b403c",
        "on-surface-variant": "#504442",
        "tertiary-fixed": "#ffdcc2",
        "surface-container-highest": "#e7e2da",
        "surface-bright": "#fef9f1",
        "on-tertiary-container": "#c38754",
        "primary": "#271310",
        "inverse-on-surface": "#f5f0e8",
        "on-tertiary-fixed-variant": "#693c0f",
        "on-tertiary-fixed": "#2e1500",
        "error-container": "#ffdad6",
        "secondary": "#79564b",
        "on-secondary-fixed": "#2d150d",
        "on-primary-container": "#ae8d87",
        "surface-tint": "#745853",
        "inverse-surface": "#32302b",
        "on-error-container": "#93000a",
        "primary-fixed": "#ffdad4",
        "background": "#fef9f1",
        "surface-container": "#f2ede5",
        "secondary-fixed-dim": "#e9bdae",
        "surface-variant": "#e7e2da",
        "on-secondary-container": "#79574c",
        "outline": "#827472",
        "tertiary": "#2a1200",
        "error": "#ba1a1a",
        "on-background": "#1d1c17",
        "surface-container-high": "#ece8e0",
        "on-primary-fixed": "#2b1613",
        "surface-container-lowest": "#ffffff",
        "surface-dim": "#ded9d2",
        "primary-container": "#3e2723",
        "inverse-primary": "#e3beb8",
        "outline-variant": "#d3c3c0",
        "on-primary": "#ffffff",
        "on-tertiary": "#ffffff",
        "tertiary-container": "#472400",
        "secondary-container": "#fed0c1"
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      spacing: {
        "container-max": "1200px",
        "unit": "4px",
        "md": "16px",
        "xl": "48px",
        "sm": "8px",
        "xs": "4px",
        "gutter": "24px",
        "lg": "24px",
        "margin-mobile": "16px"
      },
      fontFamily: {
        "body-lg": ["\"system-ui, sans-serif\""],
        "body-md": ["\"system-ui, sans-serif\""],
        "headline-sm": ["\"Georgia, serif\""],
        "caption": ["\"system-ui, sans-serif\""],
        "display-lg": ["\"Georgia, serif\""],
        "label-bold": ["\"system-ui, sans-serif\""],
        "display-lg-mobile": ["\"Georgia, serif\""],
        "headline-md": ["\"Georgia, serif\""]
      },
      fontSize: {
        "body-lg": ["18px", { "lineHeight": "1.6", "fontWeight": "400" }],
        "body-md": ["16px", { "lineHeight": "1.5", "fontWeight": "400" }],
        "headline-sm": ["24px", { "lineHeight": "1.4", "fontWeight": "600" }],
        "caption": ["12px", { "lineHeight": "1.4", "fontWeight": "400" }],
        "display-lg": ["48px", { "lineHeight": "1.1", "letterSpacing": "-0.02em", "fontWeight": "700" }],
        "label-bold": ["14px", { "lineHeight": "1.2", "letterSpacing": "0.05em", "fontWeight": "600" }],
        "display-lg-mobile": ["32px", { "lineHeight": "1.2", "fontWeight": "700" }],
        "headline-md": ["32px", { "lineHeight": "1.3", "fontWeight": "700" }]
      }
    }
  }
};
