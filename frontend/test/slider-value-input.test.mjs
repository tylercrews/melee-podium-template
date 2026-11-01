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
const { parseSliderNumber } = load("SliderValueInput.tsx");
const { default: FontSizeSlider } = load("FontSizeSlider.tsx");
const { default: RgbaColorPicker } = load("RgbaColorPicker.tsx");
const { default: ImageBackgroundSettings } = load("ImageBackgroundSettings.tsx");
const formats = load("format.ts");

function valueField(component, label) {
  return component.root.findByProps({ className: "slider-value", "aria-label": `${label} value` });
}

function type(field, text, finish = "blur") {
  act(() => field.props.onChange({ target: { value: text } }));
  if (finish === "blur") act(() => field.props.onBlur());
  else act(() => field.props.onKeyDown({ key: finish, preventDefault() {} }));
}

test("typed slider text reads the first number and ignores units", () => {
  assert.equal(parseSliderNumber("+7px"), 7);
  assert.equal(parseSliderNumber("−12 px"), -12);
  assert.equal(parseSliderNumber("2,5×"), 2.5);
  assert.equal(parseSliderNumber(".25x"), .25);
  assert.equal(parseSliderNumber("big"), null);
});

test("font size adjustments accept typed values clamped to the slider range", () => {
  const changes = [];
  let component;
  const render = (value) => createElement(FontSizeSlider, { label: "Subtitle size adjustment", value, onChange: (next) => changes.push(next) });
  act(() => { component = create(render(0)); });
  const field = valueField(component, "Subtitle size adjustment");
  assert.equal(field.props.value, "0px");
  type(field, "7", "Enter");
  type(field, "-35px");
  type(field, "3.6");
  assert.deepEqual(changes, [7, -20, 4]);
  // Escape or text without a number restores the slider's value.
  act(() => component.update(render(4)));
  type(field, "12", "Escape");
  assert.equal(valueField(component, "Subtitle size adjustment").props.value, "+4px");
  type(valueField(component, "Subtitle size adjustment"), "huge");
  assert.equal(valueField(component, "Subtitle size adjustment").props.value, "+4px");
  assert.equal(changes.length, 3);
  component.unmount();
});

test("typed opacity percentages set the RGBA alpha channel", () => {
  const changes = [];
  let component;
  act(() => { component = create(createElement(RgbaColorPicker, { label: "Main Color", value: "#123456FF", onChange: (color) => changes.push(color) })); });
  const field = valueField(component, "Main Color opacity");
  assert.equal(field.props.value, "100%");
  type(field, "50%", "Enter");
  type(field, "150");
  assert.deepEqual(changes, ["#12345680"]);
  component.unmount();
});

test("logo and background sizes accept typed multipliers within 0.001× to 100×", () => {
  let format = structuredClone(formats.EMPTY_FORMAT);
  let component;
  const render = () => createElement(ImageBackgroundSettings, { value: format, backgroundImage: null, onChange: (next) => { format = next; } });
  act(() => { component = create(render()); });
  type(valueField(component, "Tournament logo size"), "2.5x", "Enter");
  assert.equal(format.image_settings.logo_size, 2.5);
  act(() => component.update(render()));
  assert.equal(valueField(component, "Tournament logo size").props.value, "2.5×");
  type(valueField(component, "Tournament logo size"), "0.12345");
  assert.equal(format.image_settings.logo_size, .123);
  act(() => component.update(render()));
  type(valueField(component, "Background image size"), "500");
  assert.equal(format.image_settings.background_size, 100);
  act(() => component.update(render()));
  type(valueField(component, "Tournament logo size"), "0");
  assert.equal(format.image_settings.logo_size, .001);
  component.unmount();
});
