import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Product images come from the API/CDN with our own 4:5 derivatives; next/image is not used.
      "@next/next/no-img-element": "off",
    },
  },
  { ignores: [".next/**", "node_modules/**", "public/sw.js", "next-env.d.ts"] },
];
export default config;
