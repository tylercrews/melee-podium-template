import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = readFileSync(new URL("../src/podiumPreviewFooter.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { podiumHeaderWithoutFooter, drawPodiumPreviewFooter } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("clapping headers clear their old footer before the header color is applied", () => {
  const originalDocument = globalThis.document;
  try {
    const calls = [];
    const context = { drawImage: (...args) => calls.push(["draw", ...args]), clearRect: (...args) => calls.push(["clear", ...args]) };
    const layer = { getContext: () => context };
    globalThis.document = { createElement: () => layer };
    const header = {};
    assert.equal(podiumHeaderWithoutFooter(header, 1920, 941), layer);
    assert.deepEqual(calls, [["draw", header, 0, 0], ["clear", 0, 896, 1920, 45]]);
  } finally {
    globalThis.document = originalDocument;
  }
});

test("the clapping watermark follows the actual output height at 25 percent alpha", () => {
  const originalDocument = globalThis.document;
  try {
    for (const [width, height] of [[1920, 1280], [1672, 1280], [1920, 1000], [1920, 941]]) {
      const calls = [];
      const footer = { drawImage: (...args) => calls.push(["crop", ...args]), fillRect() {} };
      const layer = { getContext: () => footer };
      globalThis.document = { createElement: () => layer };
      const context = { drawImage: (...args) => calls.push(["place", ...args]) };
      const header = { naturalWidth: 1920, naturalHeight: 941 };
      drawPodiumPreviewFooter(context, header, { width, height });
      assert.deepEqual(calls[0], ["crop", header, 0, 896, 1920, 45, 0, 0, 1920, 45]);
      assert.deepEqual(calls[1], ["place", layer, 0, height - 45, width, 45]);
      assert.equal(footer.globalCompositeOperation, "source-in");
      assert.equal(footer.fillStyle, "#FFFFFF40");
    }
  } finally {
    globalThis.document = originalDocument;
  }
});
