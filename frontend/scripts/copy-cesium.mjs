// Copies CesiumJS runtime dirs into public/cesium (git-ignored). Stdlib only.
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dest = join(root, "public", "cesium");
for (const dir of ["Workers", "ThirdParty", "Assets", "Widgets"]) {
  const src = join(root, "node_modules", "cesium", "Build", "Cesium", dir);
  if (!existsSync(src)) continue;
  mkdirSync(dest, { recursive: true });
  cpSync(src, join(dest, dir), { recursive: true });
}
console.log("cesium assets ready in public/cesium");
