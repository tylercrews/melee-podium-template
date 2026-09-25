import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { BuiltInBackground, FighterOption, UserImage, UserImageCategory, builtInBackgroundUrl, deleteUserImage, getOptions, getUserImageUrl, listBuiltInBackgrounds, listUserImages, uploadUserImage } from "./api";
import { User, firebaseAuthAvailable, signInWithGoogle, signOutCurrentUser, watchCurrentUser } from "./firebaseAuth";
import FavoritesManagement from "./FavoritesManagement";
import { FavoritesData, loadFavorites, saveFavorites } from "./favorites";

const STEPS = ["Images", "Format", "Bracket Import", "Tournament", "Entrants"] as const;
const MAX_IMAGES = 10;
const MAX_IMAGE_BYTES = 300 * 1024 * 1024;
type Page = "maker" | "favorites";
interface SelectedImages { tournament_logo: string | null; background: string | null }
interface PreviewUrls { tournament_logo: string; background: string }
const EMPTY_SELECTION: SelectedImages = { tournament_logo: null, background: null };
const EMPTY_URLS: PreviewUrls = { tournament_logo: "", background: "" };
const categoryLabel = (category: UserImageCategory) => category === "tournament_logo" ? "Tournament Logo" : "Background Image";

function ImageTypeIcon({ category }: { category: UserImageCategory }) {
  return category === "tournament_logo"
    ? <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 3.5 7.4v9.2L12 21l8.5-4.4V7.4L12 3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg>
    : <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="m4 17 5.5-5.5 3.5 3 2.5-2.5 4.5 5M8 9h.01"/></svg>;
}
function TrashIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"/></svg>; }
function AccountIcon({ signedIn }: { signedIn: boolean }) { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 20c.7-4 3-6 7-6s6.3 2 7 6"/>{!signedIn && <path d="m17.5 4.5 3 3m0-3-3 3"/>}</svg>; }

function StepRail({ activeStep, maxStep, onSelect }: { activeStep: number; maxStep: number; onSelect: (index: number) => void }) {
  return <nav className="step-rail" aria-label="Image creation steps">{STEPS.map((step, index) => {
    const available = index <= maxStep;
    const complete = index < maxStep;
    return <button key={step} type="button" className={`step-tab${index === activeStep ? " step-tab--active" : ""}${complete ? " step-tab--complete" : ""}`} disabled={!available} onClick={() => onSelect(index)} aria-current={index === activeStep ? "step" : undefined}>
      <span className="step-tab__number">{complete ? "✓" : index + 1}</span><span>{step}</span>{!available && <span className="step-tab__lock" aria-label="Locked">●</span>}
    </button>;
  })}</nav>;
}

function SignInNotice({ onSignIn }: { onSignIn: () => void }) {
  return <section className="signin-notice"><span className="signin-notice__icon"><AccountIcon signedIn={false} /></span><div><h3>Sign in to use your image library</h3><p>Create an account or sign in to save and select tournament logos and backgrounds. Guest uploads are coming later.</p></div><button className="button button--light" type="button" onClick={onSignIn}>Sign in or create account</button></section>;
}

function ImageLibrary({ category, heading, images, selectedId, busyId, onSelect, onUpload, onDelete }: { category: UserImageCategory; heading?: string; images: UserImage[]; selectedId: string | null; busyId: string; onSelect: (image: UserImage) => void; onUpload: (category: UserImageCategory) => void; onDelete: (image: UserImage) => void }) {
  const atLimit = images.length >= MAX_IMAGES;
  return <section className="image-library" aria-labelledby={`${category}-heading`}>
    <div className="image-library__header"><span className="image-library__type-icon"><ImageTypeIcon category={category} /></span><div><h3 id={`${category}-heading`}>{heading ?? categoryLabel(category)}</h3><p>Your uploads · {images.length} of {MAX_IMAGES} saved</p></div>{!atLimit && <button className="button button--outline image-library__upload" type="button" onClick={() => onUpload(category)}>+ Upload</button>}</div>
    <div className="image-list">{images.length ? images.map((image) => <div className={`image-row${selectedId === image.id ? " image-row--selected" : ""}`} key={image.id}>
      <button className="image-row__select" type="button" onClick={() => onSelect(image)} disabled={busyId === image.id} aria-pressed={selectedId === image.id}><span className="image-row__radio" aria-hidden="true" /><span className="image-row__name">{image.name}</span><span className="image-row__size">{image.width} × {image.height}</span></button>
      <button className="icon-button icon-button--danger" type="button" aria-label={`Delete ${image.name}`} onClick={() => onDelete(image)} disabled={Boolean(busyId)}><TrashIcon /></button>
    </div>) : <div className="image-list__empty"><p>No {category === "tournament_logo" ? "logos" : "backgrounds"} saved yet.</p><button type="button" onClick={() => onUpload(category)}>Upload your first</button></div>}</div>
    {atLimit && <p className="limit-message">You’ve reached the {MAX_IMAGES}-image limit. Delete one to upload another.</p>}
  </section>;
}

function builtInBackgroundName(assetId: string): string {
  return assetId
    .replace(/^\d+_/, "")
    .replace(/_5000_5000_resaved\.png$/i, "")
    .replace(/([a-z])([A-Z])/g, "$1 $2");
}

function BuiltInBackgroundLibrary({ backgrounds, selectedId, onSelect }: { backgrounds: BuiltInBackground[]; selectedId: string | null; onSelect: (background: BuiltInBackground) => void }) {
  return <section className="image-library built-in-library" aria-labelledby="built-in-backgrounds-heading">
    <div className="image-library__header"><span className="image-library__type-icon"><ImageTypeIcon category="background" /></span><div><h3 id="built-in-backgrounds-heading">Included Backgrounds</h3><p>Provided collection · {backgrounds.length} available</p></div></div>
    <div className="built-in-list">{backgrounds.map((background) => {
      const selectionId = `builtin:${background.asset_id}`;
      return <button className={`built-in-row${selectedId === selectionId ? " built-in-row--selected" : ""}`} type="button" key={background.asset_id} onClick={() => onSelect(background)} aria-pressed={selectedId === selectionId}><span className="image-row__radio" aria-hidden="true" /><span><strong>{builtInBackgroundName(background.asset_id)}</strong><small>{background.size.width} × {background.size.height}</small></span></button>;
    })}</div>
    <p className="asset-attribution">Stage background renders by <strong>Malarki_</strong>.</p>
  </section>;
}

function Preview({ urls, onContinue }: { urls: PreviewUrls; onContinue: () => void }) {
  const hasLogo = Boolean(urls.tournament_logo);
  const hasBackground = Boolean(urls.background);
  const action = hasLogo && hasBackground
    ? { label: "Continue to Format", tone: "green" }
    : !hasLogo && !hasBackground
      ? { label: "Proceed without Logo or Background", tone: "pink" }
      : !hasLogo
        ? { label: "Proceed without Logo", tone: "blue" }
        : { label: "Proceed without Background", tone: "blue" };
  return <aside className="preview-column">
    <button className={`preview-action preview-action--${action.tone}`} type="button" onClick={onContinue}><span>{action.label}</span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg></button>
    <div className="preview-heading"><div><span className="eyebrow">Live canvas</span><h2>Image Preview</h2></div><span className="preview-heading__ratio">16:9</span></div>
    <div className={`canvas-preview${urls.background ? " canvas-preview--has-background" : ""}`}>{urls.background && <img className="canvas-preview__background" src={urls.background} alt="Selected background" />}{urls.tournament_logo && <img className="canvas-preview__logo" src={urls.tournament_logo} alt="Selected tournament logo" />}{!urls.background && !urls.tournament_logo && <div className="canvas-preview__empty"><span>MPM</span><p>Your selected images will appear here</p></div>}</div>
    <div className="preview-status"><span className={urls.background ? "is-ready" : ""}>{urls.background ? "✓" : "1"} Background</span><span className={urls.tournament_logo ? "is-ready" : ""}>{urls.tournament_logo ? "✓" : "2"} Logo</span></div>
    <p className="preview-tip"><strong>Preview tip:</strong> Your background fills the canvas and your logo is centered for now. Fine positioning will live in the Format step.</p>
  </aside>;
}

function StubStep({ step }: { step: string }) { return <section className="step-content stub-step"><span className="stub-step__number">Coming next</span><h1>{step}</h1><p>This step is scaffolded and ready for the next part of the redesign.</p></section>; }

export default function MakerApp() {
  const [page, setPage] = useState<Page>("maker");
  const [activeStep, setActiveStep] = useState(0);
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [images, setImages] = useState<UserImage[]>([]);
  const [builtInBackgrounds, setBuiltInBackgrounds] = useState<BuiltInBackground[]>([]);
  const [selected, setSelected] = useState<SelectedImages>(EMPTY_SELECTION);
  const [imagesSkipped, setImagesSkipped] = useState(false);
  const [previewUrls, setPreviewUrls] = useState<PreviewUrls>(EMPTY_URLS);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState("");
  const [uploadCategory, setUploadCategory] = useState<UserImageCategory | null>(null);
  const [uploadName, setUploadName] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [favorites, setFavorites] = useState<FavoritesData>(loadFavorites);
  const [fighters, setFighters] = useState<FighterOption[]>([]);
  const uploadDialogRef = useRef<HTMLDialogElement>(null);
  const accountDialogRef = useRef<HTMLDialogElement>(null);
  const groupedImages = useMemo(() => ({ tournament_logo: images.filter((image) => image.category === "tournament_logo"), background: images.filter((image) => image.category === "background") }), [images]);
  const bothImagesSelected = Boolean(selected.tournament_logo && selected.background);
  const imagesStepComplete = bothImagesSelected || imagesSkipped;
  const maxStep = imagesStepComplete ? 1 : 0;

  useEffect(() => watchCurrentUser((nextUser) => { setUser(nextUser); setAuthReady(true); if (!nextUser) { setImages([]); setSelected(EMPTY_SELECTION); setPreviewUrls(EMPTY_URLS); } }), []);
  useEffect(() => { getOptions().then((options) => setFighters(options.fighters)).catch(() => undefined); }, []);
  useEffect(() => { listBuiltInBackgrounds().then(setBuiltInBackgrounds).catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Could not load the included backgrounds.")); }, []);
  useEffect(() => {
    if (!user) return;
    let current = true;
    setLibraryLoading(true);
    user.getIdToken().then(listUserImages).then((items) => { if (current) { setImages(items); setLibraryLoading(false); } }).catch((error: unknown) => { if (current) { setMessage(error instanceof Error ? error.message : "Could not load your image library."); setLibraryLoading(false); } });
    return () => { current = false; };
  }, [user]);

  function openAccount() { setAuthMessage(""); accountDialogRef.current?.showModal(); }
  async function handleSignIn() { setAuthMessage(""); try { await signInWithGoogle(); accountDialogRef.current?.close(); } catch (error) { setAuthMessage(error instanceof Error ? error.message : "Could not sign in."); } }
  async function handleSignOut() { await signOutCurrentUser(); accountDialogRef.current?.close(); setImagesSkipped(false); setActiveStep(0); }
  function openUpload(category: UserImageCategory) { setUploadCategory(category); setUploadName(""); setUploadFile(null); setMessage(""); uploadDialogRef.current?.showModal(); }
  async function selectImage(image: UserImage) {
    if (!user) return;
    if (selected[image.category] === image.id) {
      setSelected((current) => ({ ...current, [image.category]: null }));
      setPreviewUrls((current) => ({ ...current, [image.category]: "" }));
      return;
    }
    setBusyId(image.id); setMessage("");
    try { const url = await getUserImageUrl(await user.getIdToken(), image.id); setSelected((current) => ({ ...current, [image.category]: image.id })); setPreviewUrls((current) => ({ ...current, [image.category]: url })); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not preview that image."); }
    finally { setBusyId(""); }
  }
  function selectBuiltInBackground(background: BuiltInBackground) {
    const selectionId = `builtin:${background.asset_id}`;
    if (selected.background === selectionId) {
      setSelected((current) => ({ ...current, background: null }));
      setPreviewUrls((current) => ({ ...current, background: "" }));
      return;
    }
    setSelected((current) => ({ ...current, background: selectionId }));
    setPreviewUrls((current) => ({ ...current, background: builtInBackgroundUrl(background.asset_id) }));
    setMessage("");
  }
  async function handleUpload(event: FormEvent) {
    event.preventDefault(); if (!user || !uploadCategory || !uploadFile) return;
    const normalizedName = uploadName.trim().replace(/\s+/g, " ");
    if (uploadFile.size > MAX_IMAGE_BYTES) { setMessage("Images must be 300 MB or smaller."); return; }
    if (groupedImages[uploadCategory].some((image) => image.name.toLocaleLowerCase() === normalizedName.toLocaleLowerCase())) { setMessage("You already have an image with that name in this category."); return; }
    setUploading(true); setMessage("");
    try { const created = await uploadUserImage(await user.getIdToken(), uploadFile, normalizedName, uploadCategory); setImages((current) => [created, ...current]); uploadDialogRef.current?.close(); await selectImage(created); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not upload that image."); }
    finally { setUploading(false); }
  }
  async function handleDelete(image: UserImage) {
    if (!user || !window.confirm("Are you sure you want to permanently delete this image?")) return;
    setBusyId(image.id); setMessage("");
    try { await deleteUserImage(await user.getIdToken(), image.id); setImages((current) => current.filter((item) => item.id !== image.id)); if (selected[image.category] === image.id) { setSelected((current) => ({ ...current, [image.category]: null })); setPreviewUrls((current) => ({ ...current, [image.category]: "" })); setActiveStep(0); } }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not delete that image."); }
    finally { setBusyId(""); }
  }
  const displayName = user?.displayName || user?.email || "Signed in";

  return <div className="app-shell">
    <header className="topbar"><button className="brand" type="button" onClick={() => { setPage("maker"); setActiveStep(0); }} aria-label="Melee Podium Maker home"><img className="brand__mark" src={`${import.meta.env.BASE_URL}favicon.png`} alt="" /><span>Melee Podium Maker</span></button><div className="topbar__actions"><button className="button button--nav" type="button" onClick={() => setPage(page === "maker" ? "favorites" : "maker")}>{page === "maker" ? "Manage Favorite Entrants" : "Image Maker"}</button><button className={`account-button${user ? " account-button--signed-in" : ""}`} type="button" onClick={openAccount} aria-label={user ? `Account: ${displayName}` : "Sign in"}>{user?.photoURL ? <img src={user.photoURL} alt="" /> : <AccountIcon signedIn={Boolean(user)} />}<span className="account-button__dot" /></button></div></header>
    {page === "favorites" ? <div className="favorites-redesign"><FavoritesManagement favorites={favorites} fighters={fighters} renderCount={null} onChange={(nextFavorites) => setFavorites(saveFavorites(nextFavorites))} onBack={() => setPage("maker")} /></div> : <main className="maker-layout"><section className="workflow-column"><StepRail activeStep={activeStep} maxStep={maxStep} onSelect={setActiveStep} />{activeStep === 0 ? <section className="step-content"><div className="step-intro"><span className="eyebrow">Step 1 of 5</span><h1>Choose your images</h1><p>Select the artwork that sets the stage. Both images are optional, and you can fine-tune cropping and placement in the next step.</p></div>{!authReady ? <div className="loading-card">Checking your account…</div> : !user ? <SignInNotice onSignIn={openAccount} /> : <div className="library-owner"><span>Signed in as</span><strong>{displayName}</strong></div>}<div className="image-libraries"><BuiltInBackgroundLibrary backgrounds={builtInBackgrounds} selectedId={selected.background} onSelect={selectBuiltInBackground} />{user && !libraryLoading && <><ImageLibrary category="tournament_logo" heading="Your Tournament Logos" images={groupedImages.tournament_logo} selectedId={selected.tournament_logo} busyId={busyId} onSelect={selectImage} onUpload={openUpload} onDelete={handleDelete} /><ImageLibrary category="background" heading="Your Backgrounds" images={groupedImages.background} selectedId={selected.background} busyId={busyId} onSelect={selectImage} onUpload={openUpload} onDelete={handleDelete} /></>}</div>{user && libraryLoading && <div className="loading-card">Loading your image library…</div>}{message && <p className="inline-message" role="alert">{message}</p>}<div className="step-footer"><p>Don't need a logo or background? You can add them later.</p><button className="button button--ghost" type="button" onClick={() => { setImagesSkipped(true); setActiveStep(1); }}>Skip for now</button></div><p className="future-note"><strong>Guest uploads:</strong> To do — stress-test browser memory limits before enabling unsaved local image uploads.</p></section> : <StubStep step={STEPS[activeStep]} />}</section><Preview urls={previewUrls} onContinue={() => { if (!bothImagesSelected) setImagesSkipped(true); setActiveStep(1); }} /></main>}
    <dialog className="modal" ref={accountDialogRef} onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}><div className="modal__content"><button className="modal__close" type="button" onClick={() => accountDialogRef.current?.close()} aria-label="Close">×</button>{user ? <><span className="modal__icon"><AccountIcon signedIn /></span><h2>{displayName}</h2><p>Your private image library is connected.</p><button className="button button--dark" type="button" onClick={handleSignOut}>Sign out</button></> : <><span className="modal__icon"><AccountIcon signedIn={false} /></span><h2>Welcome to the maker</h2><p>Sign in or create an account with Google to save tournament assets securely.</p><button className="button button--google" type="button" onClick={handleSignIn} disabled={!firebaseAuthAvailable}><span>G</span> Continue with Google</button>{!firebaseAuthAvailable && <p className="modal__warning">Sign-in needs the Firebase Web SDK environment values for this deployment.</p>}</>}{authMessage && <p className="inline-message" role="alert">{authMessage}</p>}</div></dialog>
    <dialog className="modal" ref={uploadDialogRef} onClick={(event) => { if (event.target === event.currentTarget && !uploading) event.currentTarget.close(); }}><form className="modal__content" onSubmit={handleUpload}><button className="modal__close" type="button" onClick={() => uploadDialogRef.current?.close()} aria-label="Close" disabled={uploading}>×</button><span className="eyebrow">Add to library</span><h2>Upload {uploadCategory ? categoryLabel(uploadCategory).toLowerCase() : "image"}</h2><label className="field">Image name<input maxLength={80} value={uploadName} onChange={(event) => setUploadName(event.target.value)} placeholder="e.g. Summer Weekly" required autoFocus /></label><label className="file-field"><input type="file" accept=".png,.jpg,.jpeg,.webp,.gif,.bmp,image/png,image/jpeg,image/webp,image/gif,image/bmp" onChange={(event: ChangeEvent<HTMLInputElement>) => setUploadFile(event.target.files?.[0] ?? null)} required /><span>{uploadFile ? uploadFile.name : "Choose a PNG, JPG, WebP, GIF, or BMP"}</span></label><p className="field-help">Names must be unique within this image category. Maximum file size: 300 MB.</p>{message && <p className="inline-message" role="alert">{message}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => uploadDialogRef.current?.close()} disabled={uploading}>Cancel</button><button className="button button--dark" type="submit" disabled={uploading || !uploadFile || !uploadName.trim()}>{uploading ? "Uploading…" : "Upload image"}</button></div></form></dialog>
  </div>;
}
