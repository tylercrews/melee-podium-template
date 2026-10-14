import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { build } from "esbuild";
import { createElement, useState } from "react";
import { act, create } from "react-test-renderer";

async function load(name) {
  const result = await build({
    entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic",
    external: ["react", "react/jsx-runtime"],
    define: { "import.meta.env.BASE_URL": '"/"' },
    plugins: [{ name: "offline-import", setup(build) {
      build.onResolve({ filter: /^\.\/api$/ }, () => ({ path: "api", namespace: "test" }));
      build.onLoad({ filter: /.*/, namespace: "test" }, () => ({ loader: "js", contents: `
        export async function importBracket(...args) { globalThis.importRequests.push(args); return globalThis.importFixture; }
        export const fighterStockIconUrl = () => '';
      ` }));
    } }],
  });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}

const { normalizeBracketImport, withCharacterImportMode, buildBracketReview } = await load("bracket.ts");
const { entrantDraftsFromBracket } = await load("creationData.ts");
const { EMPTY_FORMAT, normalizeFormat, formatCode, parseFormatCode } = await load("format.ts");
const { default: BracketStep } = await load("BracketStep.tsx");
const emptyFavorites = { version: 1, singles: [], doubles: [] };
const character = (fighter, color = "default") => ({ fighter, color, pose: "a", mirrorHorizontally: false });
const fox = character("Fox", "red");
const marth = character("Marth");
const six = ["Fox", "Falco", "Marth", "Sheik", "Peach", "Pikachu"].map((name) => character(name));
function fixture() {
  return { provider: "start.gg", tournament: { title: "Weekly", event_format: "singles" }, entrants: [
    { tag: "Winner", placement: 1, characters: [fox], won_characters: [fox], played_characters: [fox, marth] },
    { tag: "Winless", placement: 7, characters: six, won_characters: [], played_characters: six },
    { tag: "No reports", placement: 7, characters: [], won_characters: [], played_characters: [] },
  ] };
}

test("both character histories survive toggles and entrant conversion without truncation", () => {
  const source = normalizeBracketImport(fixture());
  const all = withCharacterImportMode(source, true);
  assert.deepEqual(all.entrants[0].characters, [fox, marth]);
  const wins = withCharacterImportMode(all, false);
  assert.deepEqual(wins.entrants[0].characters, [fox]);
  assert.deepEqual(wins.entrants[0].played_characters, [fox, marth]);
  const drafts = entrantDraftsFromBracket(buildBracketReview(wins, emptyFavorites, "singles"), "singles");
  assert.deepEqual(drafts[1].characters, six);
  assert.equal(drafts[2].characters[0].fighter, "Sandbag");
  assert.deepEqual(source.entrants[0].characters, [fox]);
});

test("member selections toggle independently for doubles", () => {
  const source = normalizeBracketImport({ tournament: { title: "Weekly" }, entrants: [{ tag: "Team", placement: 1,
    members: [{ tag: "One", characters: [fox], played_characters: [fox, marth], won_characters: [fox] },
      { tag: "Two", characters: six, played_characters: six, won_characters: [] }],
  }] });
  const all = withCharacterImportMode(source, true);
  assert.deepEqual(all.entrants[0].members[0].characters, [fox, marth]);
  const wins = withCharacterImportMode(all, false);
  assert.deepEqual(wins.entrants[0].members[0].characters, [fox]);
  assert.deepEqual(wins.entrants[0].members[1].characters, six);
});

test("format codes restore either checkbox value and migrate older layouts", () => {
  for (const value of [false, true]) {
    const format = { ...EMPTY_FORMAT, bracket_import_settings: { import_all_characters: value } };
    assert.equal(parseFormatCode(formatCode(format)).bracket_import_settings.import_all_characters, value);
    assert.equal(normalizeFormat({ ...format, selection: null }).bracket_import_settings.import_all_characters, value);
  }
  const old = JSON.parse(formatCode(EMPTY_FORMAT));
  delete old.bracket_import_settings;
  assert.equal(normalizeFormat(old).bracket_import_settings.import_all_characters, false);
  for (const invalid of ["false", null, 0]) {
    assert.throws(() => normalizeFormat({ ...EMPTY_FORMAT, bracket_import_settings: { import_all_characters: invalid } }), /must be true or false/);
  }
});

test("checkbox uses loaded preference, updates imported entrants immediately, and preserves favorite decisions", async () => {
  globalThis.importRequests = [];
  globalThis.importFixture = fixture();
  let latestReview;
  let latestFormat;
  const favorites = { ...emptyFavorites, singles: [{ id: "favorite", tag: "Winner", aliases: [], primary: true, characters: [marth] }] };
  function Harness() {
    const [format, setFormat] = useState(parseFormatCode(formatCode({ ...EMPTY_FORMAT, bracket_import_settings: { import_all_characters: true } })));
    const [review, setReview] = useState(null);
    latestReview = review;
    latestFormat = format;
    return createElement(BracketStep, { url: "start.gg/tournament/weekly/event/singles", review, favorites,
      eventFormat: "singles", entrantCount: 3,
      importAllCharacters: format.bracket_import_settings.import_all_characters,
      onImportAllCharactersChange: (value) => setFormat({ ...format, bracket_import_settings: { import_all_characters: value } }),
      onUrlChange() {}, onReviewChange: setReview, onSkip() {},
    });
  }
  let renderer;
  await act(async () => { renderer = create(createElement(Harness)); });
  const checkbox = () => renderer.root.findByProps({ type: "checkbox" });
  assert.equal(checkbox().props.checked, true);
  await act(async () => { await renderer.root.findByType("form").props.onSubmit({ preventDefault() {} }); });
  assert.equal(globalThis.importRequests[0][2], true);
  assert.equal(latestReview.corrections[0].accepted, true);
  await act(async () => { checkbox().props.onChange({ target: { checked: false } }); });
  assert.equal(latestFormat.bracket_import_settings.import_all_characters, false);
  assert.deepEqual(latestReview.source.entrants[0].characters, [fox]);
  assert.deepEqual(entrantDraftsFromBracket(latestReview, "singles")[0].characters, [marth]);
  const revert = renderer.root.findAllByType("button").find((button) => button.props.children === "Use bracket entrant");
  await act(async () => { revert.props.onClick(); });
  assert.equal(latestReview.corrections[0].accepted, false);
  await act(async () => { checkbox().props.onChange({ target: { checked: true } }); });
  assert.equal(latestReview.corrections[0].accepted, false);
  assert.deepEqual(entrantDraftsFromBracket(latestReview, "singles")[0].characters, [fox, marth]);
  assert.equal(globalThis.importRequests.length, 1);
  await act(async () => { renderer.unmount(); });
});
