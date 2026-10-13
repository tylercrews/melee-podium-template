import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = readFileSync(new URL("../src/previewDownload.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { previewDownloadName } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("animated render downloads use the actual GIF media type", () => {
  assert.equal(previewDownloadName("Melee Weekly #42", "image/gif"), "melee-weekly-42.gif");
  assert.equal(previewDownloadName("", "IMAGE/GIF; charset=binary"), "melee-podium.gif");
});

test("still renders retain PNG download names", () => {
  assert.equal(previewDownloadName("Melee Weekly #42", "image/png"), "melee-weekly-42.png");
  assert.equal(previewDownloadName("   ", "image/png"), "melee-podium.png");
});
