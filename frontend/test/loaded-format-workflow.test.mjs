import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { build } from "esbuild";
import { createElement } from "react";
import { act, create } from "react-test-renderer";

const api = `
const fixture = () => globalThis.makerFixture;
export const listSavedFormats = async () => fixture().saved;
export const listBuiltInBackgrounds = async () => fixture().backgrounds;
export const listProvidedFonts = async () => [{ asset_id: 'tyrowo', name: 'Tyrowo', size_adjustment: 0 }, { asset_id: 'ubuntu', name: 'Ubuntu', size_adjustment: 0 }];
export const listUserImages = async () => fixture().images;
export const listUserFonts = async () => fixture().fonts;
export const getUserImageUrl = async (_, id) => fixture().imageUrl(id);
export const getUserFontUrl = async (_, id) => '/font/' + id;
export const getOptions = async () => ({ fighters: [] });
export const getStats = async () => ({ render_count: 0 });
export const builtInBackgroundUrl = id => '/background/' + id;
export const builtInBackgroundThumbnailUrl = id => '/thumbnail/' + id;
export const providedFontUrl = id => '/font/' + id;
export const deleteUserFont = async () => {};
export const deleteUserImage = async () => {};
export const uploadUserFont = async () => {};
export const uploadUserImage = async () => {};
`;
const stubs = new Set(["EmailAuthForm", "SavedDataManagement", "BracketStep", "TournamentStep", "EntrantsStep", "FormatStep", "FormatPreview", "Footer"]);
async function loadModule(name) {
  const result = await build({
    entryPoints: [fileURLToPath(new URL(`../src/${name}`, import.meta.url))],
    bundle: true, platform: "node", format: "cjs", write: false, jsx: "automatic",
    external: ["react", "react/jsx-runtime"], define: { "import.meta.env.BASE_URL": '"/"' },
    plugins: [{ name: "offline-ui", setup(build) {
      build.onResolve({ filter: /^\.\/(api|firebaseAuth|favorites|EmailAuthForm|SavedDataManagement|BracketStep|TournamentStep|EntrantsStep|FormatStep|FormatPreview|Footer)$/ }, ({ path }) => ({ path: path.slice(2), namespace: "test" }));
      build.onLoad({ filter: /.*/, namespace: "test" }, ({ path }) => {
        const contents = path === "api" ? api : path === "firebaseAuth" ? `
          export const watchCurrentUser = callback => { callback(globalThis.makerFixture.user); return () => {}; };
          export const firebaseAuthAvailable = true;
          export const firebaseAuthErrorMessage = () => '';
          export const signInWithGoogle = async () => {};
          export const signOutCurrentUser = async () => {};
        ` : path === "favorites" ? `
          export const loadFavorites = () => ({ version: 1, singles: [], doubles: [] });
          export const saveFavorites = value => value;
          export const favoriteForImport = () => undefined;
          export const resolvedFavoriteTag = (_, tag) => tag;
        ` : stubs.has(path) ? `import { createElement } from 'react'; export default function ${path}(props) { return createElement('test-${path}', props); }` : "";
        return { contents, loader: "js" };
      });
    } }],
  });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(createRequire(import.meta.url), module, module.exports);
  return module.exports;
}

const { default: MakerApp } = await loadModule("MakerApp.tsx");
const { default: ImageBackgroundSettings } = await loadModule("ImageBackgroundSettings.tsx");
const { QUICK_PICKS, quickPickFormat } = await loadModule("quickPicks.ts");
const { EMPTY_FORMAT, formatCode } = await loadModule("format.ts");
const battlefield = "00_Battlefield_5000_5000_resaved.png";
const destination = "01_FinalDestination_5000_5000_resaved.png";
globalThis.window = new EventTarget();
globalThis.document = { fonts: { add() {}, delete() {} } };
globalThis.FontFace = class { load() { return Promise.resolve(this); } };

function fixture(overrides = {}) {
  globalThis.makerFixture = {
    user: null, saved: [], images: [], fonts: [], imageUrl: async id => `/image/${id}`,
    backgrounds: [battlefield, destination].map(asset_id => ({ asset_id, size: { width: 5000, height: 5000 } })),
    ...overrides,
  };
}
const user = { getIdToken: async () => "offline-token", displayName: "Test user" };
const text = node => node.children.map(child => typeof child === "string" ? child : text(child)).join("");
const button = (app, label) => app.root.findAllByType("button").find(node => text(node).replace(/●$/, "") === label);
const preview = app => app.root.findByType("test-FormatPreview");
async function click(node) { await act(async () => node.props.onClick()); }
async function mount(overrides) {
  fixture(overrides);
  let app;
  await act(async () => { app = create(createElement(MakerApp)); });
  return app;
}
async function load(app, source, format) {
  if (source === "quick") await click(app.root.findAllByProps({ className: "quick-pick" })[0]);
  if (source === "saved") await act(async () => app.root.findByType("select").props.onChange({ target: { value: "saved" } }));
  if (source === "code") {
    await act(async () => app.root.findByType("textarea").props.onChange({ target: { value: formatCode(format) } }));
    const form = app.root.findAllByType("form").find(node => node.findAllByType("textarea").length);
    await act(async () => form.props.onSubmit({ preventDefault() {} }));
  }
}

for (const source of ["quick", "saved", "code"]) {
  test(`${source} format immediately unlocks Bracket Import and all Load continue actions`, async () => {
    const format = quickPickFormat(QUICK_PICKS[0].id);
    const app = await mount({ user: source === "saved" ? user : null, saved: [{ id: "saved", name: "My format", data: format }] });
    try {
      await load(app, source, format);
      assert.equal(button(app, "4Bracket Import").props.disabled, false);
      assert.equal(button(app, "5Tournament").props.disabled, false);
      assert.ok(button(app, "Proceed to Bracket Import"));
      const actions = app.root.findAllByType("button").filter(node => text(node) === "Continue to Bracket Import");
      assert.equal(actions.length, 2);
      await click(actions[1]);
      assert.equal(app.root.findByType("test-BracketStep").props.entrantCount, 8);
      await click(app.root.findAllByType("button").find(node => text(node).endsWith("Load")));
      await click(button(app, "Proceed to Bracket Import"));
      assert.ok(app.root.findByType("test-BracketStep"));
      await click(app.root.findAllByType("button").find(node => text(node).endsWith("Load")));
      await click(app.root.findAllByType("button").find(node => text(node) === "Continue to Bracket Import"));
      assert.ok(app.root.findByType("test-BracketStep"));
    } finally { act(() => app.unmount()); }
  });

  test(`${source} background edits and deselection survive Assets and Format navigation`, async () => {
    const format = quickPickFormat(QUICK_PICKS[0].id);
    const app = await mount({ user: source === "saved" ? user : null, saved: [{ id: "saved", name: "My format", data: format }] });
    try {
      await load(app, source, format);
      await click(app.root.findAllByType("button").find(node => text(node).endsWith("Assets")));
      const choose = () => app.root.findAllByProps({ className: "built-in-row built-in-background-row" }).find(node => text(node).includes("Final Destination"));
      await click(choose());
      const selected = app.root.findAllByProps({ "aria-pressed": true }).find(node => text(node).includes("Final Destination"));
      assert.ok(selected);
      assert.equal(previewFormat(app).image_settings.background_placement.asset_id, `builtin:${destination}`);
      await click(button(app, "Proceed to Format"));
      assert.equal(app.root.findByType("test-FormatStep").props.value.image_settings.background_placement.asset_id, `builtin:${destination}`);
      await click(app.root.findAllByType("button").find(node => text(node).endsWith("Assets")));
      await click(app.root.findAllByProps({ "aria-pressed": true }).find(node => text(node).includes("Final Destination")));
      await click(button(app, "Proceed to Format"));
      assert.equal(preview(app).props.format.image_settings.background_placement, null);
      assert.equal(preview(app).props.backgroundImage, null);
    } finally { act(() => app.unmount()); }
  });
}

// Assets uses its compact specimen preview; read the shared Format state through
// the still-mounted Preview component instead of requiring a rendered image.
function previewFormat(app) {
  return app.root.find(node => node.type?.name === "Preview").props.format;
}

test("incomplete format imports keep Bracket Import locked", async () => {
  const app = await mount();
  try {
    await load(app, "code", EMPTY_FORMAT);
    assert.equal(button(app, "4Bracket Import").props.disabled, true);
    assert.ok(button(app, "Proceed to Assets"));
    await click(button(app, "Continue to Assets"));
    assert.ok(button(app, "Skip optional images"));
  } finally { act(() => app.unmount()); }
});

test("Format retains a saved crop while background library metadata is loading", async () => {
  const format = quickPickFormat(QUICK_PICKS[0].id);
  const updates = [];
  let app;
  await act(async () => { app = create(createElement(ImageBackgroundSettings, { value: format, backgroundImage: null, onChange: value => updates.push(value) })); });
  assert.deepEqual(updates, []);
  act(() => app.unmount());
});

test("delayed private background restoration cannot overwrite a subsequent asset edit", async () => {
  const format = quickPickFormat(QUICK_PICKS[0].id);
  format.image_settings.background_placement.asset_id = "private-background";
  format.image_settings.logo_asset_id = "private-logo";
  format.text_settings.font_asset_id = "user:private-font";
  format.text_settings.font_size_adjustment = 7;
  let resolveBackground;
  const pending = new Promise(resolve => { resolveBackground = resolve; });
  const app = await mount({
    user, saved: [{ id: "saved", name: "Private format", data: format }],
    images: [
      { id: "private-background", name: "Custom background", category: "background", width: 5000, height: 5000 },
      { id: "private-logo", name: "Custom logo", category: "tournament_logo", width: 100, height: 100 },
    ],
    fonts: [{ id: "private-font", name: "Custom font", sizeBytes: 100 }],
    imageUrl: id => id === "private-background" ? pending : Promise.resolve(`/image/${id}`),
  });
  try {
    await load(app, "saved", format);
    assert.equal(preview(app).props.format.image_settings.background_placement.asset_id, "private-background");
    await click(app.root.findAllByType("button").find(node => text(node).endsWith("Assets")));
    await click(app.root.findAllByType("button").find(node => text(node).includes("Final Destination")));
    await click(app.root.findAllByType("button").find(node => text(node).includes("Custom logo") && node.props["aria-pressed"]));
    await click(app.root.findAllByType("button").find(node => text(node).startsWith("Ubuntu")));
    await act(async () => resolveBackground("/late-private-background"));
    await click(button(app, "Proceed to Format"));
    const current = preview(app).props;
    assert.equal(current.backgroundImage.id, `builtin:${destination}`);
    assert.equal(current.backgroundImage.url, `/background/${destination}`);
    assert.equal(current.format.image_settings.background_placement.asset_id, `builtin:${destination}`);
    assert.equal(current.format.image_settings.logo_asset_id, null);
    assert.equal(current.logoImage, null);
    assert.equal(current.format.text_settings.font_asset_id, "provided:ubuntu");
    assert.equal(current.format.text_settings.font_size_adjustment, 0);
  } finally { act(() => app.unmount()); }
});
