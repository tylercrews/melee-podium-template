import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import ts from "typescript";
import { buildSync } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const compiled = buildSync({ entryPoints: [fileURLToPath(new URL("../src/format.ts", import.meta.url))],
  bundle: true, platform: "node", format: "esm", write: false }).outputFiles[0].text;
const formats = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
const component = buildSync({ entryPoints: [fileURLToPath(new URL("../src/EntrantCountSettings.tsx", import.meta.url))], bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic", external: ["react", "react/jsx-runtime"] });
const module = { exports: {} };
new Function("require", "module", "exports", component.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
const EntrantCountSettings = module.exports.default;

function fixture(style = "legacy") {
  const format = structuredClone(formats.EMPTY_FORMAT);
  format.selection.options = { event_format: "singles", entrant_count: 8, variant: "four_podium", podium_style: style };
  format.image_settings.logo_asset_id = "private-logo";
  format.text_settings.font_asset_id = "user:private-font";
  return format;
}

test("old four-podium format codes migrate to animated Podiums+Clapping", () => {
  for (const style of ["legacy", "customizable"]) {
    const loaded = formats.parseFormatCode(formats.formatCode(fixture(style)));
    assert.equal(loaded.selection.options.animated, true);
    assert.equal(loaded.selection.options.variant, "four_podium");
    assert.equal(loaded.image_settings.logo_asset_id, "private-logo");
    assert.equal(loaded.text_settings.font_asset_id, "user:private-font");
  }
});

test("both checkbox values survive exported JSON and saved-record loading", () => {
  for (const animated of [true, false]) {
    const value = fixture();
    value.selection.options.animated = animated;
    assert.deepEqual(formats.parseFormatCode(formats.formatCode(value)), value);
    assert.deepEqual(formats.normalizeFormat(JSON.parse(JSON.stringify(value))), value);
    const html = renderToStaticMarkup(createElement(EntrantCountSettings, { value, onChange() {} }));
    assert.ok(html.includes("Podiums+Clapping"));
    assert.ok(html.includes("still images"));
    assert.equal(/type="checkbox"[^>]*checked=""/.test(html), animated);
  }
});

test("selecting the layout defaults on; reselection preserves off; other layouts clear animation", () => {
  const value = fixture();
  value.selection.options.variant = null;
  const clapping = formats.entrantCountOptions(value.selection).find((option) => option.variant === "four_podium");
  const selected = formats.selectEntrantCount(value, clapping);
  assert.equal(selected.selection.options.animated, true);
  selected.selection.options.animated = false;
  assert.equal(formats.selectEntrantCount(selected, clapping).selection.options.animated, false);
  const standard = formats.entrantCountOptions(value.selection).find((option) => option.entrant_count === 4);
  const switched = formats.selectEntrantCount(selected, standard);
  assert.equal(switched.selection.options.animated, false);
  assert.ok(!renderToStaticMarkup(createElement(EntrantCountSettings, { value: switched, onChange() {} })).includes('type="checkbox"'));
});

test("imports reject malformed animation values and animation on other layouts", () => {
  for (const animated of [null, "false", 0, 1]) {
    const value = fixture();
    value.selection.options.animated = animated;
    assert.throws(() => formats.normalizeFormat(value), /Animated/);
  }
  const value = fixture();
  value.selection.options.variant = null;
  value.selection.options.animated = true;
  assert.throws(() => formats.normalizeFormat(value), /only available/);
});

test("extended clapping choices restore animation, canvas size, and correct control counts", () => {
  for (const style of ["legacy", "customizable"]) {
    for (const [eventFormat, count, variant, height, assets] of [
      ["doubles", 8, "four_podium", 1280, 4],
      ["singles", 16, "clapping", 1000, 8],
    ]) {
      const value = fixture(style);
      value.selection.options.event_format = eventFormat;
      value.selection.options.variant = null;
      const option = formats.entrantCountOptions(value.selection).find((row) => row.entrant_count === count && row.variant === variant);
      assert.ok(option);
      const selected = formats.selectEntrantCount(value, option);
      assert.equal(selected.selection.options.animated, true);
      assert.equal(formats.formattingAssetCount(selected), assets);
      assert.deepEqual(formats.formatCanvasSize(selected), { width: style === "legacy" ? 1672 : 1920, height });
      const loaded = formats.parseFormatCode(formats.formatCode(selected));
      assert.equal(formats.isPodiumsClapping(loaded.selection), true);
      const html = renderToStaticMarkup(createElement(EntrantCountSettings, { value: loaded, onChange() {} }));
      assert.ok(html.includes("Animate the clapping portraits"));
      loaded.selection.options.animated = false;
      assert.equal(formats.parseFormatCode(formats.formatCode(loaded)).selection.options.animated, false);
    }
  }
});
