// Guardrail script (Section 3.10) to verify:
// (a) color classes whose token isn't defined in globals.css
// (b) no #hex in className
// (c) no arbitrary text-[Npx] or rounded-[Npx]
// (d) no physical direction classes (ml-, mr-, pl-, pr-, left-, right-, text-left, text-right)
import fs from "node:fs";
import path from "node:path";

const ROOTS = ["app", "components"];
const ALLOWED_EXTS = new Set([".tsx", ".ts", ".jsx", ".js"]);

// Built-in Tailwind colors allowed
const BUILTINS = new Set([
  "white", "black", "transparent", "current", "inherit"
]);

// Read globals.css to extract defined tokens
const globalsCssPath = path.join("app", "globals.css");
const definedTokens = new Set([...BUILTINS]);

if (fs.existsSync(globalsCssPath)) {
  const css = fs.readFileSync(globalsCssPath, "utf8");
  const matches = css.matchAll(/--color-([a-zA-Z0-9_-]+):/g);
  for (const m of matches) {
    definedTokens.add(m[1]);
  }
}

let errors = 0;

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "node_modules" && entry.name !== ".next") {
        walk(full);
      }
    } else if (ALLOWED_EXTS.has(path.extname(entry.name))) {
      checkFile(full);
    }
  }
}

function checkFile(file) {
  const content = fs.readFileSync(file, "utf8");
  const lines = content.split("\n");

  lines.forEach((line, i) => {
    // (b) Check for hard-coded #hex in className or string templates
    const hexMatch = line.match(/(?:className=["`'][^"'`]*#[0-9a-fA-F]{3,8}|\[#[0-9a-fA-F]{3,8}\])/);
    if (hexMatch) {
      console.error(`[check:tokens] (b) ${file}:${i + 1} Hardcoded hex in className: ${hexMatch[0]}`);
      errors++;
    }

    // (c) Check for arbitrary text-[Npx] or rounded-[Npx]
    const pxMatch = line.match(/(?:text|rounded)-\[[0-9.]+px\]/);
    if (pxMatch) {
      console.error(`[check:tokens] (c) ${file}:${i + 1} Arbitrary px value: ${pxMatch[0]}`);
      errors++;
    }

    // (d) Check for physical direction classes
    const dirMatch = line.match(/\b(?:-?(?:ml|mr|pl|pr|left|right)-[0-9.]+|text-(?:left|right))\b/);
    if (dirMatch) {
      console.error(`[check:tokens] (d) ${file}:${i + 1} Physical direction class: ${dirMatch[0]}`);
      errors++;
    }

    // (a) Check for legacy or undefined color classes: indigo-* or haldi-*
    const legacyMatch = line.match(/\b(?:bg|text|border|ring|fill|stroke|from|via|to|divide|outline)-(?:indigo|haldi)-[0-9]+\b/);
    if (legacyMatch) {
      console.error(`[check:tokens] (a) ${file}:${i + 1} Undefined legacy color class: ${legacyMatch[0]}`);
      errors++;
    }
  });
}

for (const root of ROOTS) {
  if (fs.existsSync(root)) {
    walk(root);
  }
}

if (errors > 0) {
  console.error(`\nFound ${errors} token issues.`);
  process.exit(1);
} else {
  console.log("Tokens check passed!");
}
