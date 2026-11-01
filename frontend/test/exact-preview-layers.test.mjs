import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = readFileSync(new URL("../src/exactPreviewLayers.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const { exactPreviewKeys, replaceHeaderLayers, layersWithLogo, dataUrlBlob } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

function format(overrides = {}) {
  return {
    schema_version: 1,
    selection: { mode: "podium", options: { event_format: "singles", entrant_count: 8, variant: null, podium_style: "customizable", animated: false } },
    header_layout: { top_left: "tournament_logo", top_middle: "tournament_title", top_right: "metadata" },
    image_settings: { background_color: "#00000000", logo_asset_id: null, logo_size: 1, background_size: 1, background_placement: null },
    formatting_asset_colors: { mode: "premade", preset: "smash_player_colors", colors: [] },
    entrant_text_colors: { mode: "match_podium", colors: [] },
    text_settings: {
      heading_color: "#FFFFFFFF", heading_metallic: false, font_asset_id: "provided:tyrowo", font_size_adjustment: 0,
      title_font_size_adjustment: 0, subtitle_font_size_adjustment: 0, seed_font_size_adjustment: 0,
      metadata_row_font_size_adjustments: [0], include_seeding: true, use_tournament_placing: true,
      replace_base_urls_with_icons: true, metadata_rows: [["event"]],
    },
    bracket_import_settings: { import_all_characters: false },
    ...overrides,
  };
}

function keys(value, inputs = {}) {
  return exactPreviewKeys({ format: value, fontId: "provided:tyrowo", tournament: null, entrants: null, visibility: [], logoId: null, ...inputs });
}

test("header text, assignment, and tournament changes only change the header key", () => {
  const base = keys(format());
  const edits = [
    format({ text_settings: { ...format().text_settings, title_font_size_adjustment: 12, heading_color: "#FF0000FF", heading_metallic: true } }),
    format({ text_settings: { ...format().text_settings, metadata_rows: [["date"], ["event"]], metadata_row_font_size_adjustments: [2, -2] } }),
    format({ header_layout: { top_left: "metadata", top_middle: "tournament_title", top_right: "tournament_logo" } }),
  ];
  for (const edit of edits) {
    const changed = keys(edit);
    assert.equal(changed.contentKey, base.contentKey);
    assert.notEqual(changed.headerKey, base.headerKey);
  }
  const tournament = keys(format(), { tournament: { title: "Weekly #42" } });
  assert.equal(tournament.contentKey, base.contentKey);
  assert.notEqual(tournament.headerKey, base.headerKey);
});

test("browser-drawn backgrounds and logos change neither key", () => {
  const base = keys(format());
  const images = keys(format({ image_settings: { ...format().image_settings, background_color: "#123456FF", logo_size: 3 } }), { logoId: "user:logo" });
  assert.deepEqual(images, base);
});

test("entrant, font, color, and layout changes need a complete render", () => {
  const base = keys(format());
  const changes = [
    keys(format({ text_settings: { ...format().text_settings, seed_font_size_adjustment: 4 } })),
    keys(format({ text_settings: { ...format().text_settings, font_asset_id: "provided:impact" } }), { fontId: "provided:impact" }),
    keys(format({ formatting_asset_colors: { mode: "premade", preset: "rainbow", colors: [] } })),
    keys(format({ selection: { mode: "podium", options: { ...format().selection.options, entrant_count: 4 } } })),
    keys(format(), { entrants: [{ tag: "Mew2King" }] }),
    keys(format(), { visibility: [[true, false]] }),
  ];
  for (const changed of changes) assert.notEqual(changed.contentKey, base.contentKey);
});

test("Radial's server-drawn logo and its placement need a complete render", () => {
  const radial = format({ selection: { mode: "radial", options: { ...format().selection.options, podium_style: null } } });
  const base = keys(radial, { logoId: "user:logo" });
  assert.notEqual(keys(radial).contentKey, base.contentKey);
  assert.notEqual(keys({ ...radial, image_settings: { ...radial.image_settings, logo_size: 2 } }, { logoId: "user:logo" }).contentKey, base.contentKey);
  assert.notEqual(keys({ ...radial, header_layout: { top_left: "tournament_title", top_middle: "tournament_logo", top_right: "metadata" } }, { logoId: "user:logo" }).contentKey, base.contentKey);
});

test("header layers are replaced in stack order and mismatched counts are rejected", () => {
  const layers = [{ kind: "content", id: "base" }, { kind: "header", id: "subtitle" }, { kind: "content", id: "portraits" }, { kind: "header", id: "title" }];
  const headers = [{ kind: "header", id: "new subtitle" }, { kind: "header", id: "new title" }];
  assert.deepEqual(replaceHeaderLayers(layers, headers).map((layer) => layer.id), ["base", "new subtitle", "portraits", "new title"]);
  assert.equal(replaceHeaderLayers(layers, headers.slice(1)), null);
});

test("the browser logo is drawn beneath the requested layer", () => {
  assert.deepEqual(layersWithLogo(["a", "b", "c"], 2), ["a", "b", "logo", "c"]);
  assert.deepEqual(layersWithLogo(["a", "b"], 2), ["a", "b", "logo"]);
  assert.deepEqual(layersWithLogo(["a"], 9), ["a", "logo"]);
});

test("animation data URLs decode to typed blobs", async () => {
  const blob = dataUrlBlob(`data:image/gif;base64,${Buffer.from("GIF89a-bytes").toString("base64")}`);
  assert.equal(blob.type, "image/gif");
  assert.equal(Buffer.from(await blob.arrayBuffer()).toString(), "GIF89a-bytes");
});
