import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";

function load(name) {
  const result = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}
const { entrantDraftsFromBracket, ensureEntrantDrafts } = load("creationData.ts");
const { normalizeBracketImport, buildBracketReview } = load("bracket.ts");
const sandbag = { fighter: "Sandbag", color: "default", pose: "a", mirrorHorizontally: false };
const emptyFavorites = { version: 1, singles: [], doubles: [] };
const fox = { fighter: "Fox", color: "blue", pose: "e", mirrorHorizontally: true };

test("Top 16 drafts use tournament ties and retain edits while resizing", () => {
  const drafts = ensureEntrantDrafts([], 16, "singles");
  assert.deepEqual(drafts.map((row) => row.placement), [1, 2, 3, 4, 5, 5, 7, 7, 9, 9, 9, 9, 13, 13, 13, 13]);
  drafts[15].tag = "Retained player";
  const smaller = ensureEntrantDrafts(drafts, 8, "singles");
  assert.equal(smaller.length, 16);
  assert.equal(ensureEntrantDrafts(smaller, 16, "singles")[15].tag, "Retained player");
  assert.deepEqual(ensureEntrantDrafts([], 10, "singles").slice(8).map((row) => row.placement), [9, 10]);
  assert.deepEqual(ensureEntrantDrafts([], 8, "doubles").map((row) => row.placement), [1, 2, 3, 4, 5, 5, 7, 7]);
});

function source(entrants, eventFormat = "singles") {
  return normalizeBracketImport({ provider: "start.gg", tournament: { title: "Weekly", event_format: eventFormat }, entrants });
}

test("imports with no usable character reports select Standing Sandbag", () => {
  const imported = source([
    { tag: "No games", placement: 7, characters: [] },
    { tag: "No report", placement: 7 },
    { tag: "Invalid report", placement: 9, characters: [{ fighter: "" }, null] },
  ]);
  const drafts = entrantDraftsFromBracket(buildBracketReview(imported, emptyFavorites, "singles"), "singles");
  assert.equal(drafts.length, 3);
  for (const draft of drafts) assert.deepEqual(draft.characters, [sandbag]);
  assert.deepEqual(imported.entrants[0].characters, []);
  drafts[0].characters[0].fighter = "Marth";
  assert.equal(drafts[1].characters[0].fighter, "Sandbag");
});

test("reported character choices retain costumes, poses, and mirroring", () => {
  const imported = source([{ tag: "Player", placement: 1, characters: [fox] }]);
  const [draft] = entrantDraftsFromBracket(buildBracketReview(imported, emptyFavorites, "singles"), "singles");
  assert.deepEqual(draft.characters, [fox]);
});

test("doubles fallback is applied per member without replacing reported characters", () => {
  const imported = source([{ tag: "Team", placement: 1, members: [
    { tag: "No games", characters: [] }, { tag: "Has games", characters: [fox] },
  ] }], "doubles");
  const [draft] = entrantDraftsFromBracket(buildBracketReview(imported, emptyFavorites, "doubles"), "doubles");
  assert.deepEqual(draft.entrant1.characters, [sandbag]);
  assert.deepEqual(draft.entrant2.characters, [fox]);
});

test("favorite corrections precede Sandbag and reverting restores the fallback", () => {
  const imported = source([{ tag: "Sponsor | Player", placement: 1, characters: [] }]);
  const favorites = { version: 1, doubles: [], singles: [
    { id: "favorite", tag: "Player", aliases: [], primary: true, characters: [fox] },
  ] };
  const review = buildBracketReview(imported, favorites, "singles");
  const [favorite] = entrantDraftsFromBracket(review, "singles");
  assert.deepEqual(favorite.characters, [fox]);
  assert.equal(favorite.tag, "Sponsor | Player");
  review.corrections[0].accepted = false;
  const [reverted] = entrantDraftsFromBracket(review, "singles");
  assert.deepEqual(reverted.characters, [sandbag]);
  assert.deepEqual(imported.entrants[0].characters, []);
});

test("manual entrant creation still begins without a selected character", () => {
  const [draft] = ensureEntrantDrafts([], 1, "singles");
  assert.equal(draft.characters[0].fighter, "");
});
