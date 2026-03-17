import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const testDir = path.dirname(fileURLToPath(import.meta.url));
const desktopDir = path.resolve(testDir, "..");

function readCompiledFile(fileName) {
  return fs.readFileSync(path.join(desktopDir, "dist-electron", fileName), "utf8");
}

test("compiled main process avoids broken Electron ESM patterns", () => {
  const compiledMain = readCompiledFile("main.js");

  assert.match(compiledMain, /fileURLToPath\(import\.meta\.url\)/);
  assert.doesNotMatch(compiledMain, /import\s*\{\s*[^}]*\bBrowserWindow\b[^}]*\}\s*from\s*["']electron["']/);
});

test("compiled preload avoids broken Electron ESM named imports", () => {
  const compiledPreload = readCompiledFile("preload.js");

  assert.doesNotMatch(compiledPreload, /import\s*\{\s*[^}]*\bcontextBridge\b[^}]*\}\s*from\s*["']electron["']/);
});
