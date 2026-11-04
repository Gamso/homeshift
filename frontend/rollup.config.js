import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";
import json from "@rollup/plugin-json";

export default {
  input: "src/index.ts",
  output: {
    // Served and loaded by the integration (custom_components/homeshift/frontend.py).
    file: "../custom_components/homeshift/www/homeshift-card.js",
    format: "es",
    sourcemap: false,
  },
  plugins: [
    resolve(),
    commonjs(),
    json(),
    typescript({
      tsconfig: "./tsconfig.json",
      declaration: false,
    }),
    terser(),
  ],
};
