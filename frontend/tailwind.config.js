/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        slate: { ink: "#1E2A36", soft: "#56636F" }, // graphite pencil
        concrete: "#E6E8EB", // job-site concrete background
        paper: "#FFFFFF", // the work-order slip
        rule: "#CBD2DA", // ruled lines on the slip
        tape: "#F5C518", // tape-measure yellow: record button + main action only
        carbon: "#2B4C9B", // carbon-copy blue: secondary actions, links
        flag: "#C8372D", // red pencil: needs attention
        ok: "#2F7D4F", // paid
      },
      fontFamily: {
        sans: ['"Barlow"', "system-ui", "sans-serif"],
        cond: ['"Barlow Semi Condensed"', '"Barlow"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
