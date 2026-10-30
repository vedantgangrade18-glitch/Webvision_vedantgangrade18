import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Karu — handmade, proven",
    short_name: "Karu",
    description: "Sell your handmade work with one photo and one voice note. Get verified. Get a fair price.",
    start_url: "/sell",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#FBF8F2",
    theme_color: "#1F2A6B",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
