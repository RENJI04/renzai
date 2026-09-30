import js from "@eslint/js";
import nextVitals from "eslint-config-next/core-web-vitals";
import globals from "globals";
import tseslint from "typescript-eslint";

const config = [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...nextVitals,
  { languageOptions: { globals: globals.browser } },
  { ignores: [".next/**", "node_modules/**", "coverage/**"] },
];

export default config;
