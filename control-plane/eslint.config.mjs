import { defineConfig, globalIgnores } from "eslint/config";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  // Keep the starter on the flat config export that actually runs under the pinned ESLint/Next toolchain.
  ...nextCoreWebVitals,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
  {
    rules: {
      // Docs-heavy UI: apostrophes and quotes in JSX prose are intentional.
      "react/no-unescaped-entities": "off",
      // Client pages fetch on mount via async loaders whose setState runs after
      // `await`; the synchronous-render flag is a false positive for that pattern.
      "react-hooks/set-state-in-effect": "off",
    },
  },
]);
