import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import ts from "typescript";
import { buildSync } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

async function loadTypescript(name) {
  const source = readFileSync(new URL(`../src/${name}`, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
}

function loadComponent(name) {
  const compiled = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))], bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic", external: ["react", "react/jsx-runtime"], define: { "import.meta.env.BASE_URL": '"/"' } });
  const module = { exports: {} };
  new Function("require", "module", "exports", compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports.default;
}

const formats = await loadTypescript("format.ts");
const radial = await loadTypescript("radialFormat.ts");
const FormatSettings = loadComponent("FormatSettings.tsx");

function fixture(eventFormat) {
  const value = radial.selectRadialLayout(structuredClone(formats.EMPTY_FORMAT), eventFormat);
  value.header_layout = { ...formats.DEFAULT_RADIAL_HEADER_LAYOUT };
  value.image_settings.logo_asset_id = "private-logo";
  value.image_settings.logo_size = 2.5;
  value.image_settings.background_color = "#10203080";
  value.image_settings.background_size = "scale_to_width";
  value.image_settings.background_placement = formats.buildBackgroundPlacement("private-background", { width: 4096, height: 2160 }, { width: 1920, height: 1080 }, "scale_to_width", { x: .25, y: .75 });
  value.formatting_asset_colors = { mode: "pick_1", preset: null, preset_transparency: { main_color: 0, face_color: 0, base_color: 0 }, colors: [{ main_color: "#F23838A0", face_color: "#44112280", base_color: "#080C1040", metallic: false }] };
  value.entrant_text_colors = { mode: "pick_2", colors: ["#FFFFFFFF", "#FFFF0080"], metallic: [true, false] };
  value.text_settings.font_asset_id = "user:private-font";
  value.text_settings.font_size_adjustment = 9;
  value.text_settings.heading_color = "#FFEEDDCC";
  value.text_settings.heading_metallic = true;
  value.text_settings.metadata_rows = [["event", "date"], ["entrants_count"], ["tournament_link", "stream_link"]];
  value.text_settings.metadata_row_font_size_adjustments = [0, 0, 0];
  return value;
}

test("independent format font sizes survive JSON and saved format loading", () => {
  const value = fixture("singles");
  Object.assign(value.text_settings, { title_font_size_adjustment: 20, subtitle_font_size_adjustment: -20, seed_font_size_adjustment: 7, metadata_row_font_size_adjustments: [-4, 3, 12] });
  assert.deepEqual(formats.parseFormatCode(formats.formatCode(value)), value);
  assert.deepEqual(formats.normalizeFormat(JSON.parse(JSON.stringify(value))), value);
  const html = renderToStaticMarkup(createElement(FormatSettings, { value, backgroundImage: null, onChange() {} }));
  for (const label of ["Tournament title", "Subtitle", "Seed", "Metadata row 1", "Metadata row 2", "Metadata row 3"]) {
    assert.ok(html.includes(`aria-label="${label} size adjustment"`));
  }
});

test("older formats default independent font sizes to zero", () => {
  const value = fixture("doubles");
  for (const key of ["title_font_size_adjustment", "subtitle_font_size_adjustment", "seed_font_size_adjustment", "metadata_row_font_size_adjustments"]) delete value.text_settings[key];
  const loaded = formats.normalizeFormat(value);
  assert.equal(loaded.text_settings.title_font_size_adjustment, 0);
  assert.equal(loaded.text_settings.subtitle_font_size_adjustment, 0);
  assert.equal(loaded.text_settings.seed_font_size_adjustment, 0);
  assert.deepEqual(loaded.text_settings.metadata_row_font_size_adjustments, [0, 0, 0]);
  delete value.text_settings.metadata_rows;
  value.text_settings.metadata_fields = ["event", "date"];
  assert.deepEqual(formats.normalizeFormat(value).text_settings.metadata_row_font_size_adjustments, [0, 0]);
});

test("invalid independent font sizes are rejected during import", () => {
  for (const key of ["title_font_size_adjustment", "subtitle_font_size_adjustment", "seed_font_size_adjustment"]) {
    for (const size of [-21, 21, 0.5, true, "4"]) {
      const value = fixture("singles");
      value.text_settings[key] = size;
      assert.throws(() => formats.normalizeFormat(value), /Font size adjustments/);
    }
  }
  const value = fixture("singles");
  value.text_settings.metadata_row_font_size_adjustments = [0];
  assert.throws(() => formats.normalizeFormat(value), /Metadata font sizes/);
});

test("metadata sizes follow reordered rows, keep destination sizes when merged, and reset new rows", () => {
  const rows = [["event", "date"], ["entrants_count"], ["stream_link"]];
  const sizes = [6, -8, 12];
  assert.deepEqual(formats.metadataRowSizeAdjustments(rows, sizes, [rows[2], rows[0], rows[1]]), [12, 6, -8]);
  assert.deepEqual(formats.metadataRowSizeAdjustments(rows, sizes, [["entrants_count", "event"], ["date"], ["stream_link"], ["vod_link"]]), [-8, 6, 12, 0]);
});

test("Radial has one mode thumbnail and the normal Singles/Doubles controls", () => {
  assert.deepEqual(radial.RADIAL_LAYOUT_CHOICES.map(({ eventFormat, entrantCount }) => [eventFormat, entrantCount]), [["singles", 8], ["doubles", 4]]);
  const html = renderToStaticMarkup(createElement(FormatSettings, { value: fixture("singles"), backgroundImage: null, onChange() {} }));
  assert.equal((html.match(/name="event-format"/g) ?? []).length, 2);
  assert.equal((html.match(/src="\/format_mode_thumbnails\/radial.webp"/g) ?? []).length, 1);
  assert.doesNotMatch(html, /name="radial-layout"|name="entrant-count"|radial_singles|radial_doubles/);
  assert.ok(existsSync(new URL("../public/format_mode_thumbnails/radial.webp", import.meta.url)));
});

for (const eventFormat of ["singles", "doubles"]) {
  test(`${eventFormat} Radial survives JSON export/import and saved record loading`, () => {
    const value = fixture(eventFormat);
    const imported = formats.parseFormatCode(formats.formatCode(value));
    const saved = JSON.parse(JSON.stringify({ name: "My Radial Format", schema_version: 1, data: value }));
    assert.deepEqual(imported, value);
    assert.deepEqual(formats.normalizeFormat(saved.data), value);
    assert.equal(formats.isFormatComplete(imported), true);
    assert.deepEqual(formats.formatCanvasSize(imported), { width: 1920, height: 1080 });
    const html = renderToStaticMarkup(createElement(FormatSettings, { value: imported, backgroundImage: null, onChange() {} }));
    assert.equal((html.match(/name="event-format"/g) ?? []).length, 2);
    const selected = [...html.matchAll(/<input[^>]*>/g)].map((match) => match[0]).find((tag) => tag.includes('name="event-format"') && tag.includes(`value="${eventFormat}"`));
    assert.ok(selected?.includes('checked=""'));
    assert.doesNotMatch(html, /name="radial-layout"|name="entrant-count"/);
    assert.match(html, /format_mode_thumbnails\/radial\.webp/);
  });
}

test("switching Radial layouts selects count and bracket type together", () => {
  const singles = fixture("singles");
  const doubles = radial.selectRadialLayout(singles, "doubles");
  assert.deepEqual(doubles.selection.options, { event_format: "doubles", entrant_count: 4, variant: null, podium_style: null });
  assert.deepEqual(doubles.image_settings, singles.image_settings);
  assert.deepEqual(doubles.text_settings, singles.text_settings);
  assert.deepEqual(radial.selectRadialLayout(doubles, "singles"), singles);
});

test("loading rejects unsupported Radial counts, styles, and variants", () => {
  for (const [eventFormat, entrantCount] of [["singles", 4], ["singles", 16], ["doubles", 3], ["doubles", 8]]) {
    const value = fixture(eventFormat);
    value.selection.options.entrant_count = entrantCount;
    assert.throws(() => formats.parseFormatCode(JSON.stringify(value)), /Radial formats/);
  }
  for (const patch of [{ variant: "four_podium" }, { podium_style: "legacy" }]) {
    const value = fixture("singles");
    Object.assign(value.selection.options, patch);
    assert.throws(() => formats.normalizeFormat(value));
  }
});

test("an unselected Radial layout stays incomplete and imports with the central header default", () => {
  const value = fixture("singles");
  value.selection.options.event_format = null;
  value.selection.options.entrant_count = null;
  assert.equal(formats.isFormatComplete(value), false);
  delete value.header_layout;
  assert.deepEqual(formats.normalizeFormat(value).header_layout, formats.DEFAULT_RADIAL_HEADER_LAYOUT);
});

function findInput(node, name, value) {
  if (!node || typeof node !== "object") return undefined;
  if (node.type === "input" && node.props.name === name && node.props.value === value) return node;
  for (const child of [node.props?.children].flat(Infinity)) {
    const found = findInput(child, name, value);
    if (found) return found;
  }
}

test("normal bracket controls immediately fix the Radial count", () => {
  for (const [eventFormat, count] of [["singles", 8], ["doubles", 4]]) {
    let changed;
    const tree = FormatSettings({ value: fixture(eventFormat === "singles" ? "doubles" : "singles"), backgroundImage: null, onChange(value) { changed = value; } });
    findInput(tree, "event-format", eventFormat).props.onChange();
    assert.equal(changed.selection.options.event_format, eventFormat);
    assert.equal(changed.selection.options.entrant_count, count);
    assert.equal(formats.isFormatComplete(changed), true);
  }
});

test("entering Radial honors an existing bracket selection without changing other modes", () => {
  const value = fixture("doubles");
  value.selection = { mode: "podium", options: { event_format: "doubles", entrant_count: 3, variant: null, podium_style: "legacy" } };
  let changed;
  const tree = FormatSettings({ value, backgroundImage: null, onChange(value) { changed = value; } });
  findInput(tree, "image-format", "radial").props.onChange();
  assert.equal(changed.selection.options.entrant_count, 4);
  assert.deepEqual(changed.header_layout, formats.DEFAULT_RADIAL_HEADER_LAYOUT);
  findInput(tree, "image-format", "eyes").props.onChange();
  assert.equal(changed.selection.options.entrant_count, null);
  assert.equal(changed.selection.options.event_format, "doubles");
});

test("loading a Radial bracket selection derives its fixed count when omitted", () => {
  for (const [eventFormat, count] of [["singles", 8], ["doubles", 4]]) {
    const value = fixture(eventFormat);
    value.selection.options.entrant_count = null;
    const restored = formats.normalizeFormat(value);
    assert.equal(restored.selection.options.entrant_count, count);
    assert.equal(formats.isFormatComplete(restored), true);
  }
});
