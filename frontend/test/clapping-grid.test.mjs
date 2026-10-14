import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";
import { createElement } from "react";
import { act, create } from "react-test-renderer";

function load(name) {
  const result = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic",
    external: ["react", "react/jsx-runtime"], define: { "import.meta.env.BASE_URL": '"/"' } });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}
const formats = load("format.ts");
const { CLAPPING_GRID_LAYOUTS } = load("clappingGrid.ts");
const { placementNumberPreviewPath } = load("placementNumbering.ts");
const { default: FormatSettings } = load("FormatSettings.tsx");

function base() {
  const format = structuredClone(formats.EMPTY_FORMAT);
  format.selection.options = { event_format: "singles", podium_style: "customizable", entrant_count: null, variant: null, animated: false };
  return format;
}

test("all nine grids use three podiums, full canvas dimensions, animation, and sequential defaults", () => {
  const options = formats.entrantCountOptions(base().selection).filter((row) => row.variant?.startsWith("clapping_grid_"));
  assert.equal(options.length, 9);
  assert.deepEqual([...new Set(options.map((row) => row.entrant_count))], [7, 8, 9, 11, 13, 15, 18, 21]);
  assert.equal(options.filter((row) => row.entrant_count === 15).length, 2);
  for (const option of options) {
    const format = formats.selectEntrantCount(base(), option);
    assert.equal(format.text_settings.use_tournament_placing, false);
    assert.equal(format.selection.options.animated, true);
    assert.equal(formats.isFormatComplete(format), true);
    assert.equal(formats.formattingAssetCount(format), 3);
    const layout = CLAPPING_GRID_LAYOUTS.find((row) => row.entrant_count === option.entrant_count && `clapping_grid_${row.columns}` === option.variant);
    assert.deepEqual(formats.formatCanvasSize(format), { width: 1920, height: layout.height });
    assert.equal(placementNumberPreviewPath(format), `placement_numbers/podium/customizable/singles_top_${option.entrant_count}_${option.variant}/sequential.png`);
    assert.deepEqual(formats.parseFormatCode(formats.formatCode(format)).selection, format.selection);
    delete format.text_settings.use_tournament_placing;
    assert.equal(formats.normalizeFormat(format).text_settings.use_tournament_placing, false);
    format.text_settings.use_tournament_placing = true;
    format.selection.options.animated = false;
    assert.equal(formats.normalizeFormat(format).selection.options.animated, false);
    assert.equal(formats.normalizeFormat(format).text_settings.use_tournament_placing, true);
  }
});

test("grid formats preserve assets and reject legacy, doubles, other modes, and partial rows", () => {
  const option = formats.entrantCountOptions(base().selection).find((row) => row.entrant_count === 21);
  const format = formats.selectEntrantCount(base(), option);
  format.image_settings.logo_asset_id = "user:retained-logo";
  format.text_settings.font_asset_id = "user:retained-font";
  assert.equal(formats.normalizeFormat(format).image_settings.logo_asset_id, "user:retained-logo");
  assert.equal(formats.normalizeFormat(format).text_settings.font_asset_id, "user:retained-font");
  for (const invalid of [{ podium_style: "legacy" }, { event_format: "doubles" }, { entrant_count: 20 }, { variant: "clapping_grid_7" }]) {
    const bad = structuredClone(format);
    Object.assign(bad.selection.options, invalid);
    assert.throws(() => formats.normalizeFormat(bad), /Customizable Singles/);
  }
  format.selection.mode = "eyes";
  assert.throws(() => formats.normalizeFormat(format), /Customizable Singles/);
  format.selection.mode = "podium";
  format.selection.options.podium_style = "legacy";
  assert.equal(formats.entrantCountOptions(format.selection).some((row) => row.variant?.startsWith("clapping_grid_")), false);
});

test("Format exposes Top 21 and clears its unsupported grid when switching to Legacy", () => {
  let format = base();
  let component;
  const props = () => ({ value: format, backgroundImage: null, onChange: (next) => { format = next; } });
  act(() => { component = create(createElement(FormatSettings, props())); });
  const label = component.root.findAllByType("label").find((row) => row.findAllByType("strong").some((strong) => strong.children.includes("PR Top 21 + Clapping")));
  act(() => label.findByType("input").props.onChange());
  assert.equal(format.selection.options.entrant_count, 21);
  assert.equal(format.text_settings.use_tournament_placing, false);
  act(() => component.update(createElement(FormatSettings, props())));
  const legacy = component.root.findAllByType("input").find((input) => input.props.name === "podium-style" && input.props.value === "legacy");
  act(() => legacy.props.onChange());
  assert.equal(format.selection.options.entrant_count, null);
  assert.equal(format.selection.options.variant, null);
  assert.equal(format.selection.options.animated, false);
  assert.equal(format.text_settings.use_tournament_placing, true);
  component.unmount();
});
