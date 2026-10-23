import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";

function load(name) {
  const result = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic",
    external: ["react", "react/jsx-runtime"], define: { "import.meta.env.BASE_URL": '"/"' } });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}
const { stockIconPath } = load("FavoritePicker.tsx");
const { entrantDraftsFromBracket } = load("creationData.ts");
const { normalizeBracketImport, buildBracketReview, withCharacterImportMode } = load("bracket.ts");

test("stock icon paths collapse punctuation for wireframes and existing fighters", () => {
  const expected = {
    "Wireframe-Male": "/char_assets/stock_icons/wireframe_male/00_default_wireframe_male_stock.png",
    "Wireframe-Female": "/char_assets/stock_icons/wireframe_female/00_default_wireframe_female_stock.png",
    "Dr. Mario": "/char_assets/stock_icons/dr_mario/00_default_dr_mario_stock.png",
    "Mr. Game and Watch": "/char_assets/stock_icons/mr_game_and_watch/00_default_mr_game_and_watch_stock.png",
  };
  for (const [fighter, path] of Object.entries(expected)) {
    assert.equal(stockIconPath(fighter), path);
    assert.ok(existsSync(fileURLToPath(new URL(`../public${path}`, import.meta.url))), path);
  }
});

test("imported Random stand-ins keep their paired poses in drafts and import modes", () => {
  const male = { fighter: "Wireframe-Male", color: "default", pose: "b" };
  const female = { fighter: "Wireframe-Female", color: "default", pose: "f" };
  const imported = normalizeBracketImport({ provider: "start.gg", tournament: { title: "Weekly", event_format: "singles" }, entrants: [
    { tag: "Random main", placement: 1, characters: [male, female], played_characters: [{ fighter: "Fox", color: "", pose: null }, male, female], won_characters: [male, female] },
  ] });
  for (const importAll of [false, true]) {
    const review = buildBracketReview(withCharacterImportMode(imported, importAll), { version: 1, singles: [], doubles: [] }, "singles");
    const [draft] = entrantDraftsFromBracket(review, "singles");
    assert.deepEqual(draft.characters.slice(-2).map(({ fighter, pose }) => [fighter, pose]), [["Wireframe-Male", "b"], ["Wireframe-Female", "f"]]);
  }
});
