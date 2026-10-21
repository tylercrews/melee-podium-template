import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

async function loadTypescript(name) {
  const compiled = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))], bundle: true,
    platform: "node", format: "esm", write: false }).outputFiles[0].text;
  return import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
}

function loadComponent(name) {
  const compiled = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))], bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic", external: ["react", "react/jsx-runtime"], define: { "import.meta.env.BASE_URL": '"/"' } });
  const module = { exports: {} };
  new Function("require", "module", "exports", compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports.default;
}

const formats = await loadTypescript("format.ts");
const numbering = await loadTypescript("placementNumbering.ts");
const FormatSettings = loadComponent("FormatSettings.tsx");
const FormattingAssetColorSettings = loadComponent("FormattingAssetColorSettings.tsx");

function fixture(eventFormat) {
  const value = formats.selectFixedLayout(structuredClone(formats.EMPTY_FORMAT), "flying_v", eventFormat);
  value.header_layout = { ...formats.DEFAULT_HEADER_LAYOUT };
  value.image_settings.logo_asset_id = "private-logo";
  value.entrant_text_colors = { mode: "pick_2", colors: ["#FFFFFFFF", "#FFFF0080"], metallic: [true, false] };
  value.text_settings.font_asset_id = "provided:ubuntu";
  return value;
}

function findInput(node, name, value) {
  if (!node || typeof node !== "object") return undefined;
  if (node.type === "input" && node.props.name === name && node.props.value === value) return node;
  for (const child of [node.props?.children].flat(Infinity)) {
    const found = findInput(child, name, value);
    if (found) return found;
  }
}

for (const [eventFormat, count] of [["singles", 8], ["doubles", 3]]) {
  test(`${eventFormat} Flying V is a complete portrait format that survives export and saved loading`, () => {
    const value = fixture(eventFormat);
    assert.deepEqual(value.selection.options, { event_format: eventFormat, entrant_count: count, variant: null, podium_style: null, animated: false });
    const imported = formats.parseFormatCode(formats.formatCode(value));
    assert.deepEqual(imported, value);
    assert.deepEqual(formats.normalizeFormat(JSON.parse(JSON.stringify(value))), value);
    // No recolorable shapes: completeness does not depend on a formatting palette.
    assert.equal(formats.hasFormattingAssetColors(imported), false);
    assert.equal(formats.isFormatComplete(imported), true);
    assert.deepEqual(formats.formatCanvasSize(imported), { width: 1080, height: 1920 });
    assert.equal(numbering.placementNumberPreviewPath(imported), `placement_numbers/flying_v/${eventFormat}_top_${count}/tournament.png`);
  });
}

test("Flying V uses one mode thumbnail, normal Singles/Doubles controls, and its own header labels", () => {
  const html = renderToStaticMarkup(createElement(FormatSettings, { value: fixture("singles"), backgroundImage: null, onChange() {} }));
  assert.equal((html.match(/src="\/format_mode_thumbnails\/flying_v.webp"/g) ?? []).length, 1);
  assert.equal((html.match(/name="event-format"/g) ?? []).length, 2);
  assert.doesNotMatch(html, /name="entrant-count"/);
  for (const label of ["Bottom Left", "Top Middle", "Bottom Right"]) assert.ok(html.includes(`<span>${label}</span>`), label);
  assert.ok(existsSync(new URL("../public/format_mode_thumbnails/flying_v.webp", import.meta.url)));
});

test("the bracket controls immediately fix the Flying V count", () => {
  for (const [eventFormat, count] of [["singles", 8], ["doubles", 3]]) {
    let changed;
    const tree = FormatSettings({ value: fixture(eventFormat === "singles" ? "doubles" : "singles"), backgroundImage: null, onChange(value) { changed = value; } });
    findInput(tree, "event-format", eventFormat).props.onChange();
    assert.equal(changed.selection.mode, "flying_v");
    assert.equal(changed.selection.options.entrant_count, count);
    assert.equal(formats.isFormatComplete(changed), true);
  }
});

test("entering Flying V restores its default header and fixes the existing bracket count", () => {
  const value = fixture("doubles");
  value.selection = { mode: "radial", options: { event_format: "doubles", entrant_count: 4, variant: null, podium_style: null, animated: false } };
  value.header_layout = { ...formats.DEFAULT_RADIAL_HEADER_LAYOUT };
  let changed;
  const tree = FormatSettings({ value, backgroundImage: null, onChange(next) { changed = next; } });
  findInput(tree, "image-format", "flying_v").props.onChange();
  assert.equal(changed.selection.options.entrant_count, 3);
  assert.deepEqual(changed.header_layout, { top_left: "tournament_logo", top_middle: "tournament_title", top_right: "metadata" });
});

test("loading rejects unsupported Flying V counts, styles, and variants and derives omitted counts", () => {
  for (const [eventFormat, entrantCount] of [["singles", 4], ["singles", 16], ["doubles", 4], ["doubles", 8]]) {
    const value = fixture(eventFormat);
    value.selection.options.entrant_count = entrantCount;
    assert.throws(() => formats.parseFormatCode(JSON.stringify(value)), /Flying V formats/);
  }
  for (const patch of [{ variant: "four_podium" }, { podium_style: "legacy" }, { animated: true }]) {
    const value = fixture("singles");
    Object.assign(value.selection.options, patch);
    assert.throws(() => formats.normalizeFormat(value));
  }
  for (const [eventFormat, count] of [["singles", 8], ["doubles", 3]]) {
    const value = fixture(eventFormat);
    value.selection.options.entrant_count = null;
    assert.equal(formats.normalizeFormat(value).selection.options.entrant_count, count);
  }
  const unselected = fixture("singles");
  unselected.selection.options.event_format = null;
  unselected.selection.options.entrant_count = null;
  assert.equal(formats.isFormatComplete(unselected), false);
});

test("color settings hide the shape palette and offer Smash Player Colors for entrant names", () => {
  const value = fixture("singles");
  value.entrant_text_colors = { mode: "match_podium", colors: [], metallic: [] };
  const html = renderToStaticMarkup(createElement(FormattingAssetColorSettings, { value, onChange() {} }));
  assert.doesNotMatch(html, /How do you want to pick colors|Premade palette|Legacy podium artwork/);
  assert.match(html, /<option value="match_podium"[^>]*>Smash Player Colors<\/option>/);
  assert.match(html, /only entrant name colors are customizable/);
});
