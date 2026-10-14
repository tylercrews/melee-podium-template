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
const { quickPickFormat } = load("quickPicks.ts");
const data = load("creationData.ts");
const { default: TournamentStep } = load("TournamentStep.tsx");

test("every PR layout and the Top 11 Quick Pick default to no seeds, no link, and a date range", () => {
  for (const mode of ["podium", "eyes"]) {
    const base = structuredClone(formats.EMPTY_FORMAT);
    base.selection = { mode, options: { event_format: "singles", podium_style: mode === "podium" ? "customizable" : null, entrant_count: null, variant: null, animated: false } };
    for (const option of formats.entrantCountOptions(base.selection)) {
      const format = formats.selectEntrantCount(base, option);
      const pr = !formats.defaultTournamentPlacing(format.selection);
      assert.equal(format.text_settings.include_seeding, !pr);
      assert.equal(format.text_settings.metadata_rows.flat().includes("tournament_link"), !pr);
      assert.equal(format.text_settings.metadata_rows.flat().includes("date_range"), pr);
      assert.equal(format.text_settings.metadata_rows.flat().includes("date"), !pr);
      delete format.text_settings;
      const loaded = formats.normalizeFormat(format);
      assert.equal(loaded.text_settings.include_seeding, !pr);
      assert.equal(loaded.text_settings.metadata_rows.flat().includes("date_range"), pr);
    }
  }
  const pick = quickPickFormat("podiums-clapping-pr-top-11");
  assert.equal(pick.text_settings.include_seeding, false);
  assert.deepEqual(pick.text_settings.metadata_rows, [["event"], ["date_range"], ["entrants_count"]]);
});

test("explicit saved PR overrides survive format codes and row offsets survive default transitions", () => {
  const pick = quickPickFormat("podiums-clapping-pr-top-11");
  pick.text_settings.include_seeding = true;
  pick.text_settings.use_tournament_placing = true;
  pick.text_settings.metadata_rows = [["date", "tournament_link"], ["free_text_1", "free_text_4"]];
  pick.text_settings.metadata_row_font_size_adjustments = [5, -3];
  const loaded = formats.parseFormatCode(formats.formatCode(pick));
  assert.deepEqual(loaded.text_settings, pick.text_settings);
  const base = structuredClone(formats.EMPTY_FORMAT);
  base.selection = { ...pick.selection, options: { ...pick.selection.options, entrant_count: 3, variant: null, animated: false } };
  base.text_settings.metadata_rows = [["tournament_link"], ["date", "free_text_2"], ["free_text_4"]];
  base.text_settings.metadata_row_font_size_adjustments = [10, 7, -4];
  const pr = formats.selectEntrantCount(base, { entrant_count: 11, variant: "clapping_grid_4" });
  assert.deepEqual(pr.text_settings.metadata_rows, [["date_range", "free_text_2"], ["free_text_4"]]);
  assert.deepEqual(pr.text_settings.metadata_row_font_size_adjustments, [7, -4]);
  const regular = formats.selectEntrantCount(pr, { entrant_count: 3, variant: null });
  assert.equal(regular.text_settings.include_seeding, true);
  assert.deepEqual(regular.text_settings.metadata_rows, [["tournament_link"], ["date", "free_text_2"], ["free_text_4"]]);
  assert.deepEqual(regular.text_settings.metadata_row_font_size_adjustments, [0, 7, -4]);
});

test("date ranges require two valid ordered dates and free text is required only when selected", () => {
  const value = data.emptyTournamentDetails();
  value.title = "Spring PR";
  for (const [start, end, expected] of [["2026-01-01", "2026-06-30", true], ["2026-01-01", "2026-01-01", true],
    ["", "2026-06-30", false], ["2026-01-01", "", false], ["2026-02-30", "2026-06-30", false], ["2026-07-01", "2026-06-30", false]]) {
    value.dateRangeStart = start; value.dateRangeEnd = end;
    assert.equal(data.isTournamentComplete(value, ["date_range"]), expected);
  }
  assert.equal(data.isTournamentComplete(value, []), true);
  for (let index = 1; index <= 4; index++) {
    const field = `free_text_${index}`;
    assert.equal(data.METADATA_FIELD_DETAILS[field].label, `Free Text Field ${index}`);
    assert.equal(data.isTournamentComplete(value, [field]), false);
    value[`freeText${index}`] = `Custom wording ${index}`;
    assert.equal(data.isTournamentComplete(value, [field]), true);
  }
});

test("Tournament presents two date inputs and four editable free-text fields", () => {
  let value = data.emptyTournamentDetails();
  let component;
  const props = () => ({ value, selectedFields: ["date_range", "free_text_1", "free_text_2", "free_text_3", "free_text_4"],
    complete: false, onChange: next => { value = next; }, onProceed() {} });
  act(() => { component = create(createElement(TournamentStep, props())); });
  const dates = component.root.findAllByType("input").filter(input => input.props.type === "date");
  assert.equal(dates.length, 2);
  act(() => dates[0].props.onChange({ target: { value: "2026-01-01" } }));
  act(() => component.update(createElement(TournamentStep, props())));
  const end = component.root.findAllByType("input").filter(input => input.props.type === "date")[1];
  assert.equal(end.props.min, "2026-01-01");
  act(() => end.props.onChange({ target: { value: "2026-06-30" } }));
  assert.equal(value.dateRangeEnd, "2026-06-30");
  const labels = component.root.findAllByType("label");
  for (let index = 1; index <= 4; index++) {
    const label = labels.find(label => label.children.includes(`Free Text Field ${index}`));
    assert.ok(label);
    act(() => label.findByType("input").props.onChange({ target: { value: `Value ${index}` } }));
    act(() => component.update(createElement(TournamentStep, props())));
    assert.equal(value[`freeText${index}`], `Value ${index}`);
  }
  act(() => component.unmount());
});
