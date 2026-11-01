import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";
import { createElement, useState } from "react";
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
const { seedEntrantTextColors } = load("entrantTextColors.ts");
const { default: FormattingAssetColorSettings } = load("FormattingAssetColorSettings.tsx");
const { default: RgbaColorPicker } = load("RgbaColorPicker.tsx");

const MEDALS = { colors: ["#D4AF37FF", "#BEC6D2FF", "#B87333FF", "#707070FF"], metallic: [true, true, true, false] };

function medalPodiums(entrantCount = 3) {
  const format = structuredClone(formats.EMPTY_FORMAT);
  format.selection.options = { event_format: "singles", podium_style: "customizable", entrant_count: entrantCount, variant: null, animated: false };
  format.formatting_asset_colors = { ...format.formatting_asset_colors, preset: "olympic_medals" };
  return format;
}

function render(initial, matchEntrantTextColors) {
  const state = { format: initial };
  function Harness() {
    const [format, setFormat] = useState(initial);
    state.format = format;
    return createElement(FormattingAssetColorSettings, { value: format, onChange: setFormat, matchEntrantTextColors });
  }
  let component;
  act(() => { component = create(createElement(Harness)); });
  return { state, component };
}

function textModeSelect(component) {
  return component.root.findAllByType("select").find((select) => select.findAllByType("option").some((option) => option.props.value === "match_podium"));
}

async function settle(callback = () => {}) {
  await act(async () => { callback(); await new Promise((resolve) => setTimeout(resolve, 0)); });
}

test("Pick all starts from the colors and Metallic finishes that matching renders", async () => {
  const requests = [];
  const { state, component } = render(medalPodiums(), async (payload) => { requests.push(payload); return { colors: MEDALS.colors.slice(0, 3), metallic: MEDALS.metallic.slice(0, 3) }; });
  await settle(() => textModeSelect(component).props.onChange({ target: { value: "pick_all" } }));
  assert.deepEqual(state.format.entrant_text_colors, { mode: "pick_all", colors: MEDALS.colors.slice(0, 3), metallic: [true, true, true] });
  assert.deepEqual(requests, [{ mode: "podium", style: "customizable", event_format: "singles", entrant_count: 3, variant: null,
    formatting_asset_colors: state.format.formatting_asset_colors }]);
  assert.equal(textModeSelect(component).props.disabled, false);
  component.unmount();
});

test("explicit picks keep their slots while new slots match the podiums", async () => {
  const format = medalPodiums();
  format.entrant_text_colors = { mode: "pick_1", colors: ["#FFFFFFFF"], metallic: [false] };
  const { state, component } = render(format, async () => ({ colors: MEDALS.colors.slice(0, 3), metallic: MEDALS.metallic.slice(0, 3) }));
  await settle(() => textModeSelect(component).props.onChange({ target: { value: "pick_all" } }));
  assert.deepEqual(state.format.entrant_text_colors, { mode: "pick_all", colors: ["#FFFFFFFF", "#BEC6D2FF", "#B87333FF"], metallic: [false, true, true] });
  // Narrowing needs no lookup and keeps the remaining picks.
  await settle(() => textModeSelect(component).props.onChange({ target: { value: "pick_2" } }));
  assert.deepEqual(state.format.entrant_text_colors, { mode: "pick_2", colors: ["#FFFFFFFF", "#BEC6D2FF"], metallic: [false, true] });
  component.unmount();
});

test("a larger layout seeds its added entrants from the matched colors", async () => {
  const format = medalPodiums(4);
  format.entrant_text_colors = { mode: "pick_all", colors: ["#FFFFFFFF", "#FFFFFFFF", "#FFFFFFFF"], metallic: [false, false, false] };
  const { state, component } = render(format, async () => MEDALS);
  await settle();
  assert.deepEqual(state.format.entrant_text_colors, { mode: "pick_all", colors: ["#FFFFFFFF", "#FFFFFFFF", "#FFFFFFFF", "#707070FF"], metallic: [false, false, false, false] });
  component.unmount();
});

test("an unavailable lookup or unfinished layout falls back to the default palette", async () => {
  const { state, component } = render(medalPodiums(), async () => { throw new Error("offline"); });
  await settle(() => textModeSelect(component).props.onChange({ target: { value: "pick_2" } }));
  assert.deepEqual(state.format.entrant_text_colors, { mode: "pick_2", colors: ["#E53935FF", "#2878E8FF"], metallic: [false, false] });
  assert.equal(textModeSelect(component).props.disabled, false);
  component.unmount();
  const unfinished = structuredClone(formats.EMPTY_FORMAT);
  assert.deepEqual(seedEntrantTextColors(unfinished.entrant_text_colors, "pick_1", 3, null, () => "#E53935FF"), { mode: "pick_1", colors: ["#E53935FF"], metallic: [false] });
});

test("color pickers offer the saved palettes and keep the chosen opacity", () => {
  const changes = [];
  let component;
  act(() => { component = create(createElement(RgbaColorPicker, { label: "Main Color", value: "#12345680", onChange: (color) => changes.push(color) })); });
  const swatches = component.root.findAllByProps({ className: "rgba-picker__saved-color" });
  assert.equal(swatches.length, 17);
  const labels = swatches.map((swatch) => swatch.props["aria-label"]);
  for (const name of ["Red", "Blue", "Yellow", "Green", "Orange", "Cyan", "Magenta", "Gray"]) assert.ok(labels.includes(`Smash Player Colors ${name}`));
  for (const name of ["Gold", "Silver", "Bronze"]) assert.ok(labels.includes(`Olympic Medals ${name}`));
  assert.deepEqual(swatches.slice(-4).map((swatch) => [swatch.props["aria-label"], swatch.props.style.background]), [
    ["Neutrals White", "#FFFFFFFF"], ["Neutrals Very Light Gray", "#D9D9D9FF"], ["Neutrals Very Dark Gray", "#303030FF"], ["Neutrals Black", "#000000FF"]]);
  act(() => swatches.find((swatch) => swatch.props["aria-label"] === "Olympic Medals Gold").props.onClick());
  assert.deepEqual(changes, ["#D4AF3780"]);
  act(() => component.update(createElement(RgbaColorPicker, { label: "Main Color", value: "#D4AF3780", onChange() {} })));
  assert.deepEqual(component.root.findAllByProps({ className: "rgba-picker__saved-color" }).filter((swatch) => swatch.props["aria-pressed"]).map((swatch) => swatch.props["aria-label"]), ["Olympic Medals Gold"]);
  component.unmount();
});
