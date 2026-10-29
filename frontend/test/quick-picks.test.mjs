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

test("guests see ten accessible thumbnail buttons in the requested order", () => {
  const html = renderToStaticMarkup(createElement(LoadStep, {
    user: null, hasLoadedFormat: false, canProceedToBracket: false, onChange() {}, onSignIn() {}, onSkip() {}, onProceedToBracket() {},
  }));
  assert.ok(html.indexOf("load-format-heading") < html.indexOf("quick-picks-heading"));
  assert.ok(html.includes("<h1>Load A Format</h1>"));
  assert.equal((html.match(/class="quick-pick"/g) ?? []).length, 10);
  for (const pick of QUICK_PICKS) {
    assert.ok(html.includes(pick.name));
    assert.ok(html.includes(`/quick_pick_thumbnails/${pick.id}.webp`));
  }
  const buttons = html.match(/<button\b[^>]*class="quick-pick"[^>]*>/g) ?? [];
  assert.equal(buttons.length, 10);
  assert.ok(buttons.every((button) => !button.includes("disabled=")));
  assert.ok(html.includes('alt="Eyes singles Top 8 example"'));
  assert.ok(html.includes('alt="Radial singles Top 8 example"'));
  assert.ok(html.includes('alt="Animated Podiums+Clapping singles Top 11 example"'));
  assert.deepEqual(QUICK_PICKS.map(({ id }) => id), [
    "podiums-clapping-singles-top-8", "podium-doubles-top-4", "squares-singles-top-8",
    "podium-singles-top-8", "squares-doubles-top-4",
    "podiums-clapping-pr-top-11", "eyes-singles-top-8", "radial-singles-top-8", "flying-v-singles-top-8", "flying-v-doubles-top-3",
  ]);
  for (let index = 1; index < QUICK_PICKS.length; index++) {
    assert.ok(html.indexOf(QUICK_PICKS[index - 1].name) < html.indexOf(QUICK_PICKS[index].name));
  }
});

test("all ten Quick Picks load complete editable formats with their own thumbnails", () => {
  assert.deepEqual(QUICK_PICKS.map(({ mode, event_format, entrant_count }) => [mode, event_format, entrant_count]), [
    ["podium", "singles", 8], ["podium", "doubles", 4], ["squares", "singles", 8], ["podium", "singles", 8], ["squares", "doubles", 4],
    ["podium", "singles", 11], ["eyes", "singles", 8], ["radial", "singles", 8], ["flying_v", "singles", 8], ["flying_v", "doubles", 3],
  ]);
  assert.equal(QUICK_PICKS[2].name, "Just Give Me Top8er");
  for (const pick of QUICK_PICKS) {
    const format = quickPickFormat(pick.id);
    assert.equal(isFormatComplete(format), true);
    assert.deepEqual(parseFormatCode(formatCode(format)), format);
    assert.equal(format.text_settings.font_asset_id, "provided:ubuntu");
    assert.equal(format.image_settings.logo_asset_id, null);
    assert.equal(format.formatting_asset_colors.preset, "smash_player_colors");
    assert.equal(format.selection.options.podium_style, pick.podium_style ?? null);
    const placement = format.image_settings.background_placement;
    const output = formatCanvasSize(format);
    assert.equal(placement.asset_id, "builtin:00_Battlefield_5000_5000_resaved.png");
    assert.deepEqual(placement.destination, { left: 0, top: 0, right: output.width, bottom: output.height });
    assert.deepEqual(placement.alignment, { x: .5, y: .5 });
    assert.ok(existsSync(new URL(`../public/quick_pick_thumbnails/${pick.id}.webp`, import.meta.url)));
  }
});

test("the first animated Quick Pick loads Podiums+Clapping and remains editable after saving", () => {
  assert.equal(QUICK_PICKS[0].name, "The First Animated Melee Top 8 Template");
  const format = quickPickFormat(QUICK_PICKS[0].id);
  assert.equal(format.selection.options.podium_style, "customizable");
  assert.equal(format.selection.options.variant, "four_podium");
  assert.equal(format.selection.options.animated, true);
  format.selection.options.animated = false;
  assert.equal(parseFormatCode(formatCode(format)).selection.options.animated, false);
  for (const pick of QUICK_PICKS.filter((item) => !item.animated)) {
    assert.equal(quickPickFormat(pick.id).selection.options.animated, false);
    assert.equal(quickPickFormat(pick.id).selection.options.variant, null);
  }
});

test("Flying V Quick Picks load their fixed layouts with the Flying V header default", () => {
  for (const [id, eventFormat, count, canvas] of [
    ["flying-v-singles-top-8", "singles", 8, { width: 1440, height: 1920 }],
    ["flying-v-doubles-top-3", "doubles", 3, { width: 2160, height: 1080 }],
  ]) {
    const format = quickPickFormat(id);
    assert.equal(format.selection.mode, "flying_v");
    assert.equal(format.selection.options.event_format, eventFormat);
    assert.equal(format.selection.options.entrant_count, count);
    assert.equal(format.selection.options.variant, null);
    assert.deepEqual(format.header_layout, { top_left: "tournament_logo", top_middle: "tournament_title", top_right: "metadata" });
    assert.deepEqual(formatCanvasSize(format), canvas);
  }
});

test("new PR Quick Pick uses three podiums, eight animated portraits, and sequential numbers", () => {
  const pick = QUICK_PICKS[5];
  assert.equal(pick.name, "MeleePodium Also Has Some PR Settings");
  const format = quickPickFormat(pick.id);
  assert.equal(format.selection.options.entrant_count, 11);
  assert.equal(format.selection.options.variant, "clapping_grid_4");
  assert.equal(format.selection.options.podium_style, "customizable");
  assert.equal(format.selection.options.animated, true);
  assert.equal(format.text_settings.use_tournament_placing, false);
  assert.deepEqual(formatCanvasSize(format), { width: 1920, height: 1340 });
  for (const pick of QUICK_PICKS.slice(6)) {
    assert.equal(quickPickFormat(pick.id).text_settings.use_tournament_placing, true);
  }
  format.selection.options.animated = false;
  format.text_settings.use_tournament_placing = true;
  const loaded = parseFormatCode(formatCode(format));
  assert.equal(loaded.selection.options.animated, false);
  assert.equal(loaded.text_settings.use_tournament_placing, true);
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
