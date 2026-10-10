import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

async function loadModule(name) {
  const compiled = await build({
    entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic",
    external: ["react", "react/jsx-runtime"],
    define: { "import.meta.env.BASE_URL": '"/"' },
    plugins: [{ name: "offline-api", setup(build) {
      build.onResolve({ filter: /^\.\/api$/ }, () => ({ path: "api", namespace: "test" }));
      build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ contents: "export async function listSavedFormats() { return []; }", loader: "js" }));
    } }],
  });
  const module = { exports: {} };
  new Function("require", "module", "exports", compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}

const { QUICK_PICKS, quickPickFormat } = await loadModule("quickPicks.ts");
const { isFormatComplete, parseFormatCode, formatCode, formatCanvasSize } = await loadModule("format.ts");
const { default: LoadStep } = await loadModule("LoadStep.tsx");

test("guests see four accessible thumbnail buttons below the previous-format loader", () => {
  const html = renderToStaticMarkup(createElement(LoadStep, {
    user: null, hasLoadedFormat: false, onChange() {}, onSignIn() {}, onSkip() {}, onQuickPick() {}, onProceedToBracket() {},
  }));
  assert.ok(html.indexOf("load-format-heading") < html.indexOf("quick-picks-heading"));
  assert.equal((html.match(/class="quick-pick"/g) ?? []).length, 4);
  for (const pick of QUICK_PICKS) {
    assert.ok(html.includes(pick.name));
    assert.ok(html.includes(`/quick_pick_thumbnails/${pick.id}.webp`));
  }
  const buttons = html.match(/<button\b[^>]*class="quick-pick"[^>]*>/g) ?? [];
  assert.equal(buttons.length, 4);
  assert.ok(buttons.every((button) => !button.includes("disabled=")));
});

test("all four Quick Picks load complete editable formats with their own thumbnails", () => {
  assert.deepEqual(QUICK_PICKS.map(({ mode, event_format, entrant_count }) => [mode, event_format, entrant_count]), [
    ["podium", "singles", 8], ["podium", "doubles", 4], ["squares", "singles", 8], ["squares", "doubles", 4],
  ]);
  assert.equal(QUICK_PICKS[2].name, "Just Give Me Top8er");
  for (const pick of QUICK_PICKS) {
    const format = quickPickFormat(pick.id);
    assert.equal(isFormatComplete(format), true);
    assert.deepEqual(parseFormatCode(formatCode(format)), format);
    assert.equal(format.text_settings.font_asset_id, "provided:ubuntu");
    assert.equal(format.image_settings.logo_asset_id, null);
    assert.equal(format.formatting_asset_colors.preset, "smash_player_colors");
    assert.equal(format.selection.options.podium_style, pick.mode === "podium" ? "legacy" : null);
    const placement = format.image_settings.background_placement;
    const output = formatCanvasSize(format);
    assert.equal(placement.asset_id, "builtin:00_Battlefield_5000_5000_resaved.png");
    assert.deepEqual(placement.destination, { left: 0, top: 0, right: output.width, bottom: output.height });
    assert.deepEqual(placement.alignment, { x: .5, y: .5 });
    assert.ok(existsSync(new URL(`../public/quick_pick_thumbnails/${pick.id}.webp`, import.meta.url)));
  }
});

test("editing one Quick Pick does not change another load or shared defaults", () => {
  const first = quickPickFormat(QUICK_PICKS[0].id);
  const expected = quickPickFormat(QUICK_PICKS[0].id);
  first.text_settings.metadata_rows[0].push("stream_link");
  first.formatting_asset_colors.preset_transparency.main_color = 75;
  first.image_settings.background_placement.source_crop.left = 123;
  assert.deepEqual(quickPickFormat(QUICK_PICKS[0].id), expected);
  assert.throws(() => quickPickFormat("missing"), /Unknown Quick Pick/);
});
