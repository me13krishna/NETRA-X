/** @type {import('tailwindcss').Config} */

// Tactical Telemetry substrate (industrial-brutalist §2.2): dark CRT ground,
// white phosphor foreground, ONE accent. Chosen over Swiss Industrial Print
// because this is an analyst console, not a document -- and §2 says commit to
// one archetype, never mix.
//
// The palette keys keep their old names on purpose. `netra-purple` and
// `netra-cyan` appear ~130 times across the components; remapping the values
// converts every one of them at once instead of hand-editing class strings and
// missing some. The names now lie slightly -- worth renaming later, but not at
// the cost of a 200-line diff nobody can review.
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        netra: {
          // Deactivated CRT, not pure black (#000 reads as a hole, not a screen)
          bg: "#0A0A0A",
          surface: "#111111",
          card: "#141414",
          border: "#282828",
          hover: "#1E1E1E",

          // Hue now carries MEANING rather than brand. Previously `purple` and
          // `red` were both #E61919, so 126 of ~160 accent usages rendered the
          // same alarm colour -- which meant nothing on screen could actually
          // read as urgent, because everything did.
          //
          //   purple  -> interactive chrome, selection, focus, positive LLR
          //   red     -> critical ONLY: contradictions, rejections, negative LLR
          //   valid   -> verified / accepted / online
          //   amber   -> flagged, awaiting analyst review
          //
          // The call sites were already semantically correct: `netra-red` was
          // used for contradictions and negative scores, `netra-purple` for
          // ordinary chrome. Repointing this one token separates them without
          // touching 96 class strings.
          //
          // 9.46:1 on the #0A0A0A ground (AA passes at 4.5). Worth noting the
          // hazard red only reaches 4.26:1, which is itself a reason to keep it
          // off small text and on borders, fills and icons.
          purple: "#35C2E8",
          deepViolet: "#1E86A3",

          // Was a second accent (#19D9D0). Demoted to white phosphor so the
          // ~38 `netra-cyan` usages become plain primary text.
          cyan: "#EAEAEA",

          text: "#EAEAEA",
          muted: "#8A8A8A",
          subtle: "#5A5A5A",

          // Terminal green, permitted for status readouts only -- never as a
          // general text colour.
          valid: "#4AF626",
          amber: "#F0A020",
          red: "#E61919",
        },
      },

      // 90-degree corners, no exceptions. `rounded-xl` and friends still parse,
      // they just resolve to 0 -- so all 75 existing usages become square
      // without touching a component.
      borderRadius: {
        none: "0", sm: "0", DEFAULT: "0", md: "0",
        lg: "0", xl: "0", "2xl": "0", "3xl": "0", full: "0",
      },

      fontFamily: {
        // Macro-typography: heavy neo-grotesque for structural headers.
        display: ["var(--font-display)", "Archivo Black", "Impact", "sans-serif"],
        sans: ["var(--font-sans)", "Archivo", "system-ui", "sans-serif"],
        // Micro-typography: monospace carries all metadata, IDs and telemetry.
        mono: ["var(--font-mono)", "JetBrains Mono", "IBM Plex Mono", "monospace"],
      },

      letterSpacing: {
        // Tight enough that headline glyphs form solid architectural blocks.
        tightest: "-0.045em",
        // Generous tracking for uppercase labels, simulating a terminal matrix.
        telemetry: "0.12em",
      },

      boxShadow: {
        // Soft drop shadows are prohibited. A hard 1px offset reads as a
        // registration mark rather than depth.
        hard: "2px 2px 0 0 #000000",
        none: "none",
      },
    },
  },
  plugins: [],
};
