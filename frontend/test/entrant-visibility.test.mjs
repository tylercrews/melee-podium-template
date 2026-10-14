import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";
import { createElement } from "react";
import { act, create } from "react-test-renderer";

function load(name) {
  const result = buildSync({ entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic", external: ["react", "react/jsx-runtime"],
    define: { "import.meta.env.BASE_URL": '"/"' } });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}
const data = load("creationData.ts");
const { default: EntrantsStep } = load("EntrantsStep.tsx");
globalThis.window = { addEventListener() {}, removeEventListener() {} };

test("empty omitted slots complete validation while HMs still require player data", () => {
  for (const kind of ["singles", "doubles"]) {
    const entrants = data.ensureEntrantDrafts([], 8, kind).map((entrant) => ({ ...entrant, seed: "", omitEntrant: true }));
    assert.equal(data.areEntrantsComplete(entrants, 8, kind, true), true);
    entrants[7].omitEntrant = false;
    entrants[7].omitPlacement = true;
    assert.equal(data.areEntrantsComplete(entrants, 8, kind, true), false);
    entrants[7].omitEntrant = true;
    const retained = data.ensureEntrantDrafts(entrants, 4, kind);
    assert.equal(retained.length, 8);
    assert.equal(retained[7].omitPlacement, true);
    assert.equal(retained[7].omitEntrant, true);
  }
});

test("entrant controls toggle omission, disable details, and restore unchanged player data", () => {
  for (const kind of ["singles", "doubles"]) {
    let entrants = data.ensureEntrantDrafts([], 3, kind);
    if (kind === "singles") entrants[0].tag = "Retained Player";
    else entrants[0].teamName = "Retained Team";
    const original = structuredClone(entrants[0]);
    let component;
    const props = () => ({ value: entrants, count: 3, eventFormat: kind, includeSeeding: true, complete: false,
      fighters: [], favorites: { version: 1, singles: [], doubles: [] }, onChange: (next) => { entrants = next; }, onFavoritesChange() {}, onProceed() {} });
    act(() => { component = create(createElement(EntrantsStep, props())); });
    const controls = () => component.root.findAllByProps({ className: "entrant-visibility-controls" })[0].findAllByType("input");
    act(() => controls()[1].props.onChange({ target: { checked: true } }));
    assert.equal(entrants[0].omitPlacement, true);
    act(() => component.update(createElement(EntrantsStep, props())));
    act(() => controls()[0].props.onChange({ target: { checked: true } }));
    act(() => component.update(createElement(EntrantsStep, props())));
    assert.equal(component.root.findAllByProps({ className: "entrant-details" })[0].props.disabled, true);
    assert.equal(controls()[1].props.disabled, true);
    assert.ok(component.root.findAllByType("fieldset")[0].props.className.includes("entrant-card--omitted"));
    act(() => controls()[0].props.onChange({ target: { checked: false } }));
    act(() => component.update(createElement(EntrantsStep, props())));
    assert.equal(component.root.findAllByProps({ className: "entrant-details" })[0].props.disabled, false);
    assert.deepEqual(entrants[0], { ...original, omitEntrant: false, omitPlacement: true });
    component.unmount();
  }
});
