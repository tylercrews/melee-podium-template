import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { buildSync } from "esbuild";
import { createElement, useState } from "react";
import { act, create } from "react-test-renderer";

const compiled = buildSync({
  entryPoints: [fileURLToPath(new URL("../src/EntrantCharacterEditor.tsx", import.meta.url))],
  bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic",
  external: ["react", "react/jsx-runtime"], define: { "import.meta.env.BASE_URL": '"/"' },
});
const module = { exports: {} };
new Function("require", "module", "exports", compiled.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
const Editor = module.exports.default;

test("entrant picker selects Sandbag and previews its Standing pose", () => {
  let selected;
  function Harness() {
    const [characters, setCharacters] = useState([module.exports.createCharacterForm()]);
    selected = characters;
    return createElement(Editor, {
      tag: "Sandbag player", characters, onTagChange() {}, onChange: setCharacters,
      fighters: [{ name: "Sandbag", options: ["default", "red", "green", "blue"].map((color, index) => ({
        color, pose: "a", pose_label: "Standing", color_order: index,
        portrait: `${String(index).padStart(2, "0")}a_${color}_Sandbag_tyro-decomp-anims_standing.png`,
      })) }],
    });
  }
  let tree;
  act(() => { tree = create(createElement(Harness)); });
  const picker = tree.root.findByProps({ role: "combobox" });
  act(() => { picker.props.onFocus(); });
  const option = tree.root.findAllByType("button").find(button => button.children[0] === "Sandbag");
  assert.ok(option);
  act(() => { option.props.onMouseDown({ preventDefault() {} }); });
  assert.equal(selected[0].fighter, "Sandbag");
  assert.equal(selected[0].color, "default");
  const pose = tree.root.findAllByType("select")[1];
  assert.ok(pose.findAllByType("option").some(option => option.children[0] === "Standing"));
  act(() => { pose.props.onChange({ target: { value: "a" } }); });
  assert.equal(selected[0].pose, "a");
  assert.equal(tree.root.findByType("img").props.src,
    "/char_assets/renders/Sandbag/00a_default_Sandbag_tyro-decomp-anims_standing.png");
  const color = tree.root.findAllByType("select")[0];
  act(() => { color.props.onChange({ target: { value: "green" } }); });
  assert.equal(selected[0].color, "green");
  assert.equal(tree.root.findByType("img").props.src,
    "/char_assets/renders/Sandbag/02a_green_Sandbag_tyro-decomp-anims_standing.png");
  act(() => { tree.unmount(); });
});
