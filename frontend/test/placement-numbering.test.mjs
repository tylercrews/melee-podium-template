import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";
import { createElement } from "react";
import { act, create } from "react-test-renderer";
import { renderToStaticMarkup } from "react-dom/server";

function load(name) {
  const result = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic",
    external: ["react", "react/jsx-runtime"], define: { "import.meta.env.BASE_URL": '"/"' } });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}
const formats = load("format.ts");
const { placementNumberPreviewPath, placementRank } = load("placementNumbering.ts");
const { default: FormatSettings } = load("FormatSettings.tsx");
const { default: EntrantsStep } = load("EntrantsStep.tsx");
const { ensureEntrantDrafts } = load("creationData.ts");

test("entrant card labels follow numbering without changing retained bracket results", () => {
  const entrants = ensureEntrantDrafts([], 16, "singles");
  const props = { value: entrants, count: 16, eventFormat: "singles", includeSeeding: true, complete: false,
    fighters: [], favorites: { version: 1, singles: [], doubles: [] }, onChange() {}, onFavoritesChange() {}, onProceed() {} };
  const sequential = renderToStaticMarkup(createElement(EntrantsStep, { ...props, useTournamentPlacing: false }));
  const tournament = renderToStaticMarkup(createElement(EntrantsStep, { ...props, useTournamentPlacing: true }));
  assert.ok(sequential.includes("<legend>6th Place</legend>"));
  assert.ok(sequential.includes("<legend>16th Place</legend>"));
  assert.ok(!tournament.includes("<legend>6th Place</legend>"));
  assert.equal(entrants[5].placement, 5);
  assert.equal(entrants[15].placement, 13);
  assert.deepEqual(Array.from({ length: 16 }, (_, i) => placementRank(i + 1)), [1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13]);
});

test("saved formats and codes migrate old defaults and retain either placement checkbox value", () => {
  for (const mode of ["podium", "eyes", "squares", "radial"]) {
    const format = structuredClone(formats.EMPTY_FORMAT);
    format.selection.mode = mode;
    format.selection.options = { event_format: "singles", entrant_count: 8, variant: null, podium_style: mode === "podium" ? "legacy" : null };
    delete format.text_settings.use_tournament_placing;
    assert.equal(formats.normalizeFormat(format).text_settings.use_tournament_placing, true);
    for (const value of [true, false]) {
      format.text_settings.use_tournament_placing = value;
      const loaded = formats.parseFormatCode(formats.formatCode(format));
      assert.equal(loaded.text_settings.use_tournament_placing, value);
      assert.ok(placementNumberPreviewPath(loaded).endsWith(value ? "/tournament.png" : "/sequential.png"));
    }
    for (const bad of [null, "false", 1, 0]) {
      format.text_settings.use_tournament_placing = bad;
      assert.throws(() => formats.normalizeFormat(format), /bracket placing/);
    }
  }
});

test("PR defaults stay sequential and tournament choices default to bracket placings", () => {
  let format = structuredClone(formats.EMPTY_FORMAT);
  format.selection.mode = "eyes";
  format.selection.options = { event_format: "singles", entrant_count: null, variant: null, podium_style: null };
  const options = formats.entrantCountOptions(format.selection);
  format = formats.selectEntrantCount(format, options.find((row) => row.entrant_count === 15));
  assert.equal(format.text_settings.use_tournament_placing, false);
  delete format.text_settings.use_tournament_placing;
  assert.equal(formats.normalizeFormat(format).text_settings.use_tournament_placing, false);
  format = formats.selectEntrantCount(format, options.find((row) => row.entrant_count === 16));
  assert.equal(format.text_settings.use_tournament_placing, true);
});

test("the placement checkbox updates the live format and chooses the clapping numbering layer", () => {
  let format = structuredClone(formats.EMPTY_FORMAT);
  format.selection.options = { event_format: "doubles", entrant_count: 8, variant: "four_podium", podium_style: "customizable", animated: true };
  let component;
  act(() => { component = create(createElement(FormatSettings, { value: format, backgroundImage: null, onChange: (next) => { format = next; } })); });
  const label = component.root.findAllByType("label").find((row) => row.findAllByType("strong").some((strong) => strong.children.includes("Tournament bracket placing")));
  const checkbox = label.findByType("input");
  assert.equal(checkbox.props.checked, true);
  act(() => checkbox.props.onChange({ target: { checked: false } }));
  assert.equal(format.text_settings.use_tournament_placing, false);
  assert.equal(placementNumberPreviewPath(format), "placement_numbers/podium/customizable/doubles_top_8_four_podium/sequential.png");
  component.unmount();
});
