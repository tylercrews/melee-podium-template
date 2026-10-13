import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = readFileSync(new URL("../src/radialWatermark.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { drawRadialWatermark } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("Radial preview samples each layout and preserves watermark alpha when tinting", () => {
  const originalDocument = globalThis.document;
  try {
    const cases = [
      [[255, 255, 255, 255], "#000000FF"],
      [[0, 0, 0, 255], "#FFFFFFFF"],
      [[255, 255, 255, 0], "#FFFFFFFF"],
    ];
    for (const [pixel, expectedColor] of cases) {
      for (const doubles of [false, true]) {
        const tint = { drawImage() {}, fillRect() {} };
        const layer = { getContext: () => tint };
        globalThis.document = { createElement: () => layer };
        const calls = [];
        const context = {
          getImageData: (...args) => { calls.push(args); return { data: new Uint8ClampedArray(pixel) }; },
          drawImage: (...args) => calls.push(args),
        };
        drawRadialWatermark(context, { naturalWidth: 1920, naturalHeight: 1080 }, doubles);
        assert.deepEqual(calls[0], doubles ? [1562, 1034, 340, 28] : [1450, 962, 340, 24]);
        assert.equal(tint.globalCompositeOperation, "source-in");
        assert.equal(tint.fillStyle, expectedColor);
        assert.deepEqual(calls[1], [layer, 0, 0]);
      }
    }
  } finally {
    globalThis.document = originalDocument;
  }
});
