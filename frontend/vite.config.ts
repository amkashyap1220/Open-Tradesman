import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    // Makes the app installable: "Add to Home Screen" gives tradespeople an app icon.
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["apple-touch-icon.png", "favicon.svg"],
      manifest: {
        name: "Open Tradesman",
        short_name: "Tradesman",
        description: "Quotes, change orders and payments for tradespeople.",
        start_url: "/",
        display: "standalone",
        background_color: "#E6E8EB",
        theme_color: "#1E2A36",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Never cache API calls: money data must always be live.
        navigateFallbackDenylist: [/^\/api/],
      },
    }),
  ],
});
