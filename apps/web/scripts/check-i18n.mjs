// Checks that every translation key used in the code exists in messages/en.json, and reports how
// complete each other locale is (missing keys fall back to English at runtime).
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const en = JSON.parse(readFileSync(join(root, "messages/en.json"), "utf8"));

function flatten(obj, prefix = "", out = {}) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) flatten(v, key, out);
    else out[key] = v;
  }
  return out;
}
const enFlat = flatten(en);
const has = (key) => key in enFlat || Object.keys(enFlat).some((k) => k.startsWith(key + "."));

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    if (["node_modules", ".next", "public", "scripts"].includes(name)) continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, files);
    else if (/\.(tsx?|mjs)$/.test(name)) files.push(p);
  }
  return files;
}

const missing = new Set();
let checked = 0;
for (const file of walk(root)) {
  const src = readFileSync(file, "utf8");
  // Each call resolves to the closest preceding declaration of the same translator variable.
  const decls = [...src.matchAll(/const (\w+) = (?:await )?(?:useTranslations|getTranslations)\(\s*(?:"([^"]*)"|`([^`]*)`)?\s*\)/g)].map((m) => ({
    name: m[1],
    ns: m[2] ?? m[3] ?? "",
    at: m.index,
  }));
  for (const name of new Set(decls.map((d) => d.name))) {
    const re = new RegExp(String.raw`\b${name}(?:\.raw)?\(\s*"([^"]+)"`, "g");
    for (const m of src.matchAll(re)) {
      const decl = decls.filter((d) => d.name === name && d.at < m.index).pop();
      if (!decl || decl.ns.includes("${")) continue;
      const key = decl.ns ? `${decl.ns}.${m[1]}` : m[1];
      checked++;
      if (!has(key)) missing.add(`${key}  (${file.replace(root, "")})`);
    }
  }
}

console.log(`Checked ${checked} static keys.`);
if (missing.size) {
  console.log(`Missing in en.json (${missing.size}):`);
  for (const k of [...missing].sort()) console.log("  " + k);
}
for (const loc of ["hi", "pa", "mr", "gu", "ur", "ta", "ml"]) {
  try {
    const flat = flatten(JSON.parse(readFileSync(join(root, `messages/${loc}.json`), "utf8")));
    const total = Object.keys(enFlat).length;
    const done = Object.keys(enFlat).filter((k) => k in flat).length;
    console.log(`${loc}: ${done}/${total} keys (${Math.round((done / total) * 100)}%)`);
  } catch (e) {
    console.log(`${loc}: unreadable (${e.message})`);
  }
}
process.exit(missing.size ? 1 : 0);
