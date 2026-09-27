import {
  ChangeEvent,
  FormEvent,
  ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  FighterOption,
  SavedFormat,
  UserFont,
  UserImage,
  createSavedFormat,
  deleteSavedFormat,
  getUserFontUrl,
  getUserImageUrl,
  listSavedFormats,
  replaceSavedFormat,
} from "./api";
import EntrantCharacterEditor from "./EntrantCharacterEditor";
import { CharacterStockIcons, SinglesFavoritePicker } from "./FavoritePicker";
import { User } from "./firebaseAuth";
import {
  FavoriteDoublesTeam,
  FavoriteSinglesEntrant,
  FavoritesData,
  characterSummary,
  newFavoriteId,
  normalizeFavorites,
  normalizedFavoriteTag,
  parseAlternateSpellings,
} from "./favorites";
import Footer from "./Footer";
import { FormatConfiguration, parseFormatCode } from "./format";

type UploadKind = "tournament_logo" | "background" | "font";
type DeleteTarget =
  | { kind: "format"; item: SavedFormat }
  | { kind: "image"; item: UserImage }
  | { kind: "font"; item: UserFont };
type FavoriteDraft =
  | { kind: "singles"; entrant: FavoriteSinglesEntrant }
  | { kind: "doubles"; team: FavoriteDoublesTeam };

interface SavedDataManagementProps {
  favorites: FavoritesData;
  fighters: FighterOption[];
  renderCount: number | null;
  user: User | null;
  images: UserImage[];
  fonts: UserFont[];
  busyId: string;
  onChange: (favorites: FavoritesData) => void;
  onBack: () => void;
  onSignIn: () => void;
  onUpload: (kind: UploadKind) => void;
  onDeleteImage: (image: UserImage) => Promise<void>;
  onDeleteFont: (font: UserFont) => Promise<void>;
}

const emptyMember = (): Omit<FavoriteSinglesEntrant, "id" | "primary"> => ({
  tag: "",
  aliases: [],
  characters: [{ fighter: "", color: "", pose: "", mirrorHorizontally: false }],
});

const copyMember = (
  favorite: FavoriteSinglesEntrant,
): Omit<FavoriteSinglesEntrant, "id" | "primary"> => ({
  tag: favorite.tag,
  aliases: [...favorite.aliases],
  characters: favorite.characters.map((character) => ({ ...character })),
});

function favoriteIdentities(tag: string, aliases: string[]): Set<string> {
  return new Set(
    [tag, ...aliases]
      .map(normalizedFavoriteTag)
      .filter(Boolean),
  );
}

function identitiesOverlap(left: Set<string>, right: Set<string>): boolean {
  return [...left].some((identity) => right.has(identity));
}

function duplicateFavoriteDescriptions(
  draft: FavoriteDraft,
  favorites: FavoritesData,
): string[] {
  const existingEntrants = [
    ...favorites.singles.map((entrant) => ({
      description: `Singles entrant “${entrant.tag}”`,
      identities: favoriteIdentities(entrant.tag, entrant.aliases),
    })),
    ...favorites.doubles.flatMap((team) => ([team.entrant_1, team.entrant_2].map((entrant) => ({
      description: `“${entrant.tag}” on doubles team “${team.team_name}”`,
      identities: favoriteIdentities(entrant.tag, entrant.aliases),
    })))),
  ];
  const candidates = draft.kind === "singles"
    ? [{ label: draft.entrant.tag, identities: favoriteIdentities(draft.entrant.tag, draft.entrant.aliases) }]
    : [draft.team.entrant_1, draft.team.entrant_2].map((entrant) => ({
        label: entrant.tag,
        identities: favoriteIdentities(entrant.tag, entrant.aliases),
      }));

  return [...new Set(candidates.flatMap((candidate) =>
    existingEntrants
      .filter((existing) => identitiesOverlap(candidate.identities, existing.identities))
      .map((existing) => `${candidate.label} matches ${existing.description}`),
  ))];
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5" />
    </svg>
  );
}

function displaySavedDate(value?: string): string {
  if (!value) return "Saved format";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Saved format" : `Updated ${date.toLocaleDateString()}`;
}

export default function SavedDataManagement({
  favorites,
  fighters,
  renderCount,
  user,
  images,
  fonts,
  busyId,
  onChange,
  onBack,
  onSignIn,
  onUpload,
  onDeleteImage,
  onDeleteFont,
}: SavedDataManagementProps) {
  const favoritesInput = useRef<HTMLInputElement>(null);
  const formatImportDialog = useRef<HTMLDialogElement>(null);
  const overwriteDialog = useRef<HTMLDialogElement>(null);
  const deleteDialog = useRef<HTMLDialogElement>(null);
  const addFavoriteDialog = useRef<HTMLDialogElement>(null);
  const duplicateFavoriteDialog = useRef<HTMLDialogElement>(null);
  const [message, setMessage] = useState("");
  const [favoriteQuery, setFavoriteQuery] = useState("");
  const [favoriteMenuOpen, setFavoriteMenuOpen] = useState(false);
  const [selectedFavorite, setSelectedFavorite] = useState<string | null>(null);
  const [formats, setFormats] = useState<SavedFormat[]>([]);
  const [formatsLoading, setFormatsLoading] = useState(false);
  const [formatName, setFormatName] = useState("");
  const [formatJson, setFormatJson] = useState("");
  const [pendingFormat, setPendingFormat] = useState<{
    name: string;
    data: FormatConfiguration;
  } | null>(null);
  const [overwriteTarget, setOverwriteTarget] = useState<SavedFormat | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [working, setWorking] = useState(false);
  const [imagePreviewUrls, setImagePreviewUrls] = useState<Record<string, string>>({});
  const [fontPreviewUrls, setFontPreviewUrls] = useState<Record<string, string>>({});
  const [favoriteDraft, setFavoriteDraft] = useState<FavoriteDraft | null>(null);
  const [favoriteAliasInputs, setFavoriteAliasInputs] = useState<[string, string]>(["", ""]);
  const [duplicateFavorites, setDuplicateFavorites] = useState<string[]>([]);

  const changeSingles = (singles: FavoriteSinglesEntrant[]) =>
    onChange({ ...favorites, singles });
  const changeDoubles = (doubles: FavoriteDoublesTeam[]) =>
    onChange({ ...favorites, doubles });

  useEffect(() => {
    if (!user) {
      setFormats([]);
      return;
    }
    let current = true;
    setFormatsLoading(true);
    user
      .getIdToken()
      .then(listSavedFormats)
      .then((items) => {
        if (current) setFormats(items);
      })
      .catch((error: unknown) => {
        if (current) {
          setMessage(error instanceof Error ? error.message : "Could not load saved formats.");
        }
      })
      .finally(() => {
        if (current) setFormatsLoading(false);
      });
    return () => {
      current = false;
    };
  }, [user]);

  useEffect(() => {
    if (!user) {
      setImagePreviewUrls({});
      setFontPreviewUrls({});
      return;
    }
    let current = true;
    user.getIdToken().then(async (token) => {
      const [imageEntries, fontEntries] = await Promise.all([
        Promise.all(images.map(async (image) => [image.id, await getUserImageUrl(token, image.id)] as const)),
        Promise.all(fonts.map(async (font) => [font.id, await getUserFontUrl(token, font.id)] as const)),
      ]);
      if (!current) return;
      setImagePreviewUrls(Object.fromEntries(imageEntries));
      setFontPreviewUrls(Object.fromEntries(fontEntries));
    }).catch(() => {
      if (current) setMessage("Some saved asset previews could not be loaded.");
    });
    return () => {
      current = false;
    };
  }, [fonts, images, user]);

  const favoriteOptions = useMemo(
    () => [
      ...favorites.singles.map((favorite) => ({
        key: `single:${favorite.id}`,
        label: favorite.tag || "Untitled entrant",
        detail: characterSummary(favorite.characters),
      })),
      ...favorites.doubles.map((team) => ({
        key: `double:${team.id}`,
        label: team.team_name || "Untitled team",
        detail: `${team.entrant_1.tag} / ${team.entrant_2.tag}`,
      })),
    ],
    [favorites],
  );
  const matchingOptions = favoriteOptions.filter((option) =>
    `${option.label} ${option.detail}`
      .toLocaleLowerCase()
      .includes(favoriteQuery.trim().toLocaleLowerCase()),
  );
  const visibleSingles = selectedFavorite?.startsWith("single:")
    ? favorites.singles.filter((favorite) => `single:${favorite.id}` === selectedFavorite)
    : selectedFavorite
      ? []
      : favorites.singles;
  const visibleDoubles = selectedFavorite?.startsWith("double:")
    ? favorites.doubles.filter((team) => `double:${team.id}` === selectedFavorite)
    : selectedFavorite
      ? []
      : favorites.doubles;
  const logos = images.filter((image) => image.category === "tournament_logo");
  const backgrounds = images.filter((image) => image.category === "background");

  function addSingles() {
    setFavoriteDraft({
      kind: "singles",
      entrant: { id: newFavoriteId(), ...emptyMember(), primary: false },
    });
    setFavoriteAliasInputs(["", ""]);
    setDuplicateFavorites([]);
    addFavoriteDialog.current?.showModal();
  }

  function addDoubles() {
    setFavoriteDraft({
      kind: "doubles",
      team: {
        id: newFavoriteId(),
        team_name: "",
        team_color: "random",
        entrant_1: emptyMember(),
        entrant_2: emptyMember(),
      },
    });
    setFavoriteAliasInputs(["", ""]);
    setDuplicateFavorites([]);
    addFavoriteDialog.current?.showModal();
  }

  function commitFavoriteDraft(draft = favoriteDraft) {
    if (!draft) return;
    if (draft.kind === "singles") {
      const entrant = {
        ...draft.entrant,
        tag: draft.entrant.tag.trim(),
      };
      changeSingles([
        ...favorites.singles.map((favorite) =>
          entrant.primary && normalizedFavoriteTag(favorite.tag) === normalizedFavoriteTag(entrant.tag)
            ? { ...favorite, primary: false }
            : favorite,
        ),
        entrant,
      ]);
    } else {
      changeDoubles([
        ...favorites.doubles,
        {
          ...draft.team,
          team_name: draft.team.team_name.trim(),
          entrant_1: { ...draft.team.entrant_1, tag: draft.team.entrant_1.tag.trim() },
          entrant_2: { ...draft.team.entrant_2, tag: draft.team.entrant_2.tag.trim() },
        },
      ]);
    }
    duplicateFavoriteDialog.current?.close();
    addFavoriteDialog.current?.close();
    setFavoriteDraft(null);
    setDuplicateFavorites([]);
    setMessage("Favorite saved.");
  }

  function requestFavoriteSave(event: FormEvent) {
    event.preventDefault();
    if (!favoriteDraft) return;
    const preparedDraft: FavoriteDraft = favoriteDraft.kind === "singles"
      ? {
          ...favoriteDraft,
          entrant: { ...favoriteDraft.entrant, aliases: parseAlternateSpellings(favoriteAliasInputs[0]) },
        }
      : {
          ...favoriteDraft,
          team: {
            ...favoriteDraft.team,
            entrant_1: { ...favoriteDraft.team.entrant_1, aliases: parseAlternateSpellings(favoriteAliasInputs[0]) },
            entrant_2: { ...favoriteDraft.team.entrant_2, aliases: parseAlternateSpellings(favoriteAliasInputs[1]) },
          },
        };
    const duplicates = duplicateFavoriteDescriptions(preparedDraft, favorites);
    if (duplicates.length) {
      setFavoriteDraft(preparedDraft);
      setDuplicateFavorites(duplicates);
      duplicateFavoriteDialog.current?.showModal();
      return;
    }
    commitFavoriteDraft(preparedDraft);
  }

  function setPrimary(id: string, primary: boolean) {
    const selected = favorites.singles.find((favorite) => favorite.id === id);
    if (!selected) return;
    const tag = normalizedFavoriteTag(selected.tag);
    changeSingles(
      favorites.singles.map((favorite) =>
        normalizedFavoriteTag(favorite.tag) === tag
          ? { ...favorite, primary: favorite.id === id ? primary : false }
          : favorite,
      ),
    );
  }

  function replaceTeamMember(
    teamId: string,
    member: "entrant_1" | "entrant_2",
    favorite: FavoriteSinglesEntrant,
  ) {
    changeDoubles(
      favorites.doubles.map((team) =>
        team.id === teamId ? { ...team, [member]: copyMember(favorite) } : team,
      ),
    );
  }

  function chooseFavorite(key: string) {
    const option = favoriteOptions.find((candidate) => candidate.key === key);
    if (!option) return;
    setSelectedFavorite(key);
    setFavoriteQuery(option.label);
    setFavoriteMenuOpen(false);
  }

  function clearFavoriteFilter() {
    setSelectedFavorite(null);
    setFavoriteQuery("");
    setFavoriteMenuOpen(false);
  }

  function downloadFavorites() {
    const blob = new Blob([JSON.stringify(favorites, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "melee-podium-favorites.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function importFavorites(event: ChangeEvent<HTMLInputElement>, replace: boolean) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const imported = normalizeFavorites(JSON.parse(await file.text()));
      onChange(
        replace
          ? imported
          : {
              version: 1,
              singles: [...favorites.singles, ...imported.singles],
              doubles: [...favorites.doubles, ...imported.doubles],
            },
      );
      setMessage(replace ? "Favorites replaced from import." : "Favorites added from import.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "That favorites file could not be imported.");
    }
    event.target.value = "";
  }

  function chooseFavoritesFile(replace: boolean) {
    if (!favoritesInput.current) return;
    favoritesInput.current.dataset.replace = String(replace);
    favoritesInput.current.click();
  }

  async function saveImportedFormat(target: SavedFormat | null, pending = pendingFormat) {
    if (!user || !pending) return;
    setWorking(true);
    try {
      const token = await user.getIdToken();
      const saved = target
        ? await replaceSavedFormat(token, target.id, pending.name, pending.data)
        : await createSavedFormat(token, pending.name, pending.data);
      setFormats((current) =>
        target
          ? current.map((item) => (item.id === target.id ? saved : item))
          : [saved, ...current],
      );
      setMessage(target ? `Updated “${saved.name}”.` : `Imported “${saved.name}”.`);
      setPendingFormat(null);
      setOverwriteTarget(null);
      overwriteDialog.current?.close();
      formatImportDialog.current?.close();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save that format.");
    } finally {
      setWorking(false);
    }
  }

  function requestFormatImport(event: FormEvent) {
    event.preventDefault();
    try {
      const pending = {
        name: formatName.trim(),
        data: parseFormatCode(formatJson),
      };
      const existing = formats.find(
        (format) =>
          format.name.trim().toLocaleLowerCase() === pending.name.toLocaleLowerCase(),
      );
      setPendingFormat(pending);
      if (existing) {
        setOverwriteTarget(existing);
        formatImportDialog.current?.close();
        overwriteDialog.current?.showModal();
      } else {
        void saveImportedFormat(null, pending);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "That format code could not be imported.");
    }
  }

  function requestDelete(target: DeleteTarget) {
    setDeleteTarget(target);
    deleteDialog.current?.showModal();
  }

  async function confirmDelete() {
    if (!user || !deleteTarget) return;
    setWorking(true);
    try {
      if (deleteTarget.kind === "format") {
        await deleteSavedFormat(await user.getIdToken(), deleteTarget.item.id);
        setFormats((current) =>
          current.filter((format) => format.id !== deleteTarget.item.id),
        );
      } else if (deleteTarget.kind === "image") {
        await onDeleteImage(deleteTarget.item);
      } else {
        await onDeleteFont(deleteTarget.item);
      }
      setMessage("Deleted successfully.");
      deleteDialog.current?.close();
      setDeleteTarget(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete that item.");
    } finally {
      setWorking(false);
    }
  }

  const deleteName = deleteTarget?.item.name;

  return (
    <main className="page-shell saved-data-page">
      <header className="site-header">
        <div>
          <h1>Manage Saved Data</h1>
          <p className="lede">
            Manage the assets, formats, and favorite entrants you reuse while making tournament graphics.
          </p>
        </div>
        <button type="button" onClick={onBack}>Back to image maker</button>
      </header>

      {message && <p className="inline-message" role="status">{message}</p>}
      {!user && (
        <section className="panel saved-data-signin">
          <div>
            <h2>Sign in to manage cloud data</h2>
            <p>Favorite entrants remain available locally.</p>
          </div>
          <button className="button button--light" type="button" onClick={onSignIn}>
            Sign in or create account
          </button>
        </section>
      )}

      <section className="panel saved-data-panel" aria-labelledby="saved-assets-heading">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Assets</span>
            <h2 id="saved-assets-heading">Saved assets</h2>
            <p>Your tournament logos, backgrounds, and custom fonts.</p>
          </div>
        </div>
        {user ? (
          <div className="saved-asset-groups">
            <SavedAssetGroup title="Tournament Logos" count={logos.length} onUpload={() => onUpload("tournament_logo")}>
              {logos.map((image) => (
                <SavedAssetRow key={image.id} name={image.name} detail={`${image.width} × ${image.height}`} busy={busyId === image.id} preview={<AssetImagePreview url={imagePreviewUrls[image.id]} name={image.name} transparent />} onDelete={() => requestDelete({ kind: "image", item: image })} />
              ))}
            </SavedAssetGroup>
            <SavedAssetGroup title="Backgrounds" count={backgrounds.length} onUpload={() => onUpload("background")}>
              {backgrounds.map((image) => (
                <SavedAssetRow key={image.id} name={image.name} detail={`${image.width} × ${image.height}`} busy={busyId === image.id} preview={<AssetImagePreview url={imagePreviewUrls[image.id]} name={image.name} />} onDelete={() => requestDelete({ kind: "image", item: image })} />
              ))}
            </SavedAssetGroup>
            <SavedAssetGroup title="Custom Fonts" count={fonts.length} onUpload={() => onUpload("font")}>
              {fonts.map((font) => (
                <SavedAssetRow key={font.id} name={font.name} detail={`${Math.ceil(font.sizeBytes / 1024)} KB`} busy={busyId === font.id} preview={<SavedFontPreview id={font.id} url={fontPreviewUrls[font.id]} />} onDelete={() => requestDelete({ kind: "font", item: font })} />
              ))}
            </SavedAssetGroup>
          </div>
        ) : (
          <p className="saved-data-empty">Sign in to view your uploaded assets.</p>
        )}
      </section>

      <section className="panel saved-data-panel" aria-labelledby="saved-formats-heading">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Formats</span>
            <h2 id="saved-formats-heading">Saved formats</h2>
            <p>{formats.length} saved</p>
          </div>
          {user && (
            <button className="button button--dark" type="button" onClick={() => {
              setFormatName("");
              setFormatJson("");
              setMessage("");
              formatImportDialog.current?.showModal();
            }}>
              Import Format
            </button>
          )}
        </div>
        {formatsLoading ? (
          <p className="saved-data-empty">Loading formats…</p>
        ) : formats.length ? (
          <div className="saved-format-list">
            {formats.map((format) => (
              <article className="saved-format-row" key={format.id}>
                <div>
                  <strong>{format.name}</strong>
                  <small>{displaySavedDate(format.updatedAt ?? format.createdAt)}</small>
                </div>
                <button className="icon-button icon-button--danger" type="button" onClick={() => requestDelete({ kind: "format", item: format })} aria-label={`Delete ${format.name}`} title={`Delete ${format.name}`}>
                  <TrashIcon />
                </button>
              </article>
            ))}
          </div>
        ) : (
          <p className="saved-data-empty">
            {user ? "No saved formats yet. Import one here or save one from the Format step." : "Sign in to view saved formats."}
          </p>
        )}
      </section>

      <section className="panel saved-data-panel" aria-labelledby="favorite-entrants-heading">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Favorite Entrants</span>
            <h2 id="favorite-entrants-heading">Favorite entrants</h2>
            <p>{favorites.singles.length} singles entrants · {favorites.doubles.length} doubles teams</p>
          </div>
          <div className="inline-actions">
            <button type="button" onClick={downloadFavorites}>Export favorites</button>
            <button type="button" onClick={() => chooseFavoritesFile(false)}>Import additional</button>
            <button type="button" className="button-danger" onClick={() => chooseFavoritesFile(true)}>Replace from import</button>
            <input ref={favoritesInput} className="visually-hidden" type="file" accept="application/json" onChange={(event) => importFavorites(event, favoritesInput.current?.dataset.replace === "true")} />
          </div>
        </div>

        <div className="favorite-filter-combobox">
          <label htmlFor="favorite-filter">Filter favorite entrants</label>
          <div className="favorite-filter-combobox__input">
            <input id="favorite-filter" role="combobox" aria-expanded={favoriteMenuOpen} aria-controls="favorite-filter-options" autoComplete="off" value={favoriteQuery} placeholder="All entrants" onFocus={() => setFavoriteMenuOpen(true)} onBlur={() => window.setTimeout(() => setFavoriteMenuOpen(false), 120)} onChange={(event) => {
              setFavoriteQuery(event.target.value);
              setSelectedFavorite(null);
              setFavoriteMenuOpen(true);
            }} />
            {(selectedFavorite || favoriteQuery) && (
              <button type="button" onClick={clearFavoriteFilter} aria-label="Clear entrant filter">×</button>
            )}
          </div>
          {favoriteMenuOpen && (
            <div className="favorite-filter-combobox__menu" id="favorite-filter-options" role="listbox">
              {matchingOptions.length ? matchingOptions.map((option) => (
                <button type="button" role="option" aria-selected={selectedFavorite === option.key} key={option.key} onMouseDown={(event) => event.preventDefault()} onClick={() => chooseFavorite(option.key)}>
                  <strong>{option.label}</strong>
                  <small>{option.detail}</small>
                </button>
              )) : <p>No matching entrants.</p>}
            </div>
          )}
        </div>

        <FavoriteSinglesSection favorites={favorites} visible={visibleSingles} fighters={fighters} onAdd={addSingles} onChange={changeSingles} onSetPrimary={setPrimary} selected={Boolean(selectedFavorite)} />
        <FavoriteDoublesSection favorites={favorites} visible={visibleDoubles} fighters={fighters} onAdd={addDoubles} onChange={changeDoubles} onReplaceMember={replaceTeamMember} selected={Boolean(selectedFavorite)} />
      </section>

      <Footer renderCount={renderCount} />

      <dialog className="modal add-favorite-modal" ref={addFavoriteDialog} onClose={() => {
        setFavoriteDraft(null);
        setDuplicateFavorites([]);
      }} onClick={(event) => {
        if (event.target === event.currentTarget) event.currentTarget.close();
      }}>
        {favoriteDraft && (
          <form className="modal__content" onSubmit={requestFavoriteSave}>
            <button className="modal__close" type="button" onClick={() => addFavoriteDialog.current?.close()} aria-label="Close">×</button>
            <span className="eyebrow">Favorite entrants</span>
            <h2>{favoriteDraft.kind === "singles" ? "Add singles entrant" : "Add doubles team"}</h2>
            <p>Fill out the reusable entrant information before adding it to your saved list.</p>
            {favoriteDraft.kind === "singles" ? (
              <>
                <EntrantCharacterEditor
                  tag={favoriteDraft.entrant.tag}
                  characters={favoriteDraft.entrant.characters}
                  fighters={fighters}
                  onTagChange={(tag) => setFavoriteDraft((current) => current?.kind === "singles" ? { ...current, entrant: { ...current.entrant, tag } } : current)}
                  onChange={(characters) => setFavoriteDraft((current) => current?.kind === "singles" ? { ...current, entrant: { ...current.entrant, characters } } : current)}
                />
                <label className="field favorite-alternate-field">
                  Alternate spellings
                  <textarea value={favoriteAliasInputs[0]} onChange={(event) => setFavoriteAliasInputs([event.target.value, favoriteAliasInputs[1]])} placeholder="BUSTA, BU$TA" />
                  <small>Comma-separated spellings that should match this entrant. Sponsors and capitalization are ignored.</small>
                </label>
                <label className="choice"><input type="checkbox" checked={favoriteDraft.entrant.primary} onChange={(event) => setFavoriteDraft((current) => current?.kind === "singles" ? { ...current, entrant: { ...current.entrant, primary: event.target.checked } } : current)} /> Use this as the primary favorite when multiple saved versions match</label>
              </>
            ) : (
              <>
                <div className="row-fields">
                  <label className="field">Team name<input value={favoriteDraft.team.team_name} onChange={(event) => setFavoriteDraft((current) => current?.kind === "doubles" ? { ...current, team: { ...current.team, team_name: event.target.value } } : current)} required autoFocus /></label>
                  <label className="field">Team color<select value={favoriteDraft.team.team_color} onChange={(event) => setFavoriteDraft((current) => current?.kind === "doubles" ? { ...current, team: { ...current.team, team_color: event.target.value } } : current)}><option value="random">Random</option><option value="red">Red</option><option value="green">Green</option><option value="blue">Blue</option></select></label>
                </div>
                {(["entrant_1", "entrant_2"] as const).map((member, index) => (
                  <fieldset className="add-favorite-member" key={member}>
                    <legend>Entrant {index + 1}</legend>
                    <SinglesFavoritePicker
                      favorites={favorites.singles}
                      label={`Use favorited entrant for entrant ${index + 1}`}
                      onChoose={(favorite) => {
                        setFavoriteDraft((current) => current?.kind === "doubles" ? { ...current, team: { ...current.team, [member]: copyMember(favorite) } } : current);
                        setFavoriteAliasInputs((current) => index === 0 ? [favorite.aliases.join(", "), current[1]] : [current[0], favorite.aliases.join(", ")]);
                      }}
                    />
                    <EntrantCharacterEditor
                      tag={favoriteDraft.team[member].tag}
                      tagLabel={`Entrant ${index + 1} tag`}
                      characters={favoriteDraft.team[member].characters}
                      fighters={fighters}
                      onTagChange={(tag) => setFavoriteDraft((current) => current?.kind === "doubles" ? { ...current, team: { ...current.team, [member]: { ...current.team[member], tag } } } : current)}
                      onChange={(characters) => setFavoriteDraft((current) => current?.kind === "doubles" ? { ...current, team: { ...current.team, [member]: { ...current.team[member], characters } } } : current)}
                    />
                    <label className="field favorite-alternate-field">
                      Alternate spellings
                      <textarea value={favoriteAliasInputs[index]} onChange={(event) => setFavoriteAliasInputs(index === 0 ? [event.target.value, favoriteAliasInputs[1]] : [favoriteAliasInputs[0], event.target.value])} placeholder="BUSTA, BU$TA" />
                      <small>Comma-separated spellings for entrant {index + 1}.</small>
                    </label>
                  </fieldset>
                ))}
              </>
            )}
            <div className="modal__actions">
              <button className="button button--ghost" type="button" onClick={() => addFavoriteDialog.current?.close()}>Cancel</button>
              <button className="button button--dark" type="submit">Save favorite</button>
            </div>
          </form>
        )}
      </dialog>

      <dialog className="modal" ref={duplicateFavoriteDialog} onClick={(event) => {
        if (event.target === event.currentTarget) event.currentTarget.close();
      }}>
        <div className="modal__content">
          <button className="modal__close" type="button" onClick={() => duplicateFavoriteDialog.current?.close()} aria-label="Close">×</button>
          <span className="eyebrow">Possible duplicate</span>
          <h2>Save another favorite?</h2>
          <p>One or more tags or alternate spellings match entrant information you already saved:</p>
          <ul className="duplicate-favorite-list">
            {duplicateFavorites.map((duplicate) => <li key={duplicate}>{duplicate}</li>)}
          </ul>
          <p>You can return to edit the new favorite, or confirm that you want to keep another saved version.</p>
          <div className="modal__actions">
            <button className="button button--ghost" type="button" onClick={() => duplicateFavoriteDialog.current?.close()}>Back to edit</button>
            <button className="button button--dark" type="button" onClick={() => commitFavoriteDraft()}>Save another</button>
          </div>
        </div>
      </dialog>

      <dialog className="modal format-code-modal" ref={formatImportDialog} onClick={(event) => {
        if (event.target === event.currentTarget && !working) event.currentTarget.close();
      }}>
        <form className="modal__content" onSubmit={requestFormatImport}>
          <button className="modal__close" type="button" onClick={() => formatImportDialog.current?.close()} aria-label="Close" disabled={working}>×</button>
          <span className="eyebrow">Saved formats</span>
          <h2>Import Format</h2>
          <p>Paste a format code and choose the name it should use.</p>
          <label className="field">Format name<input value={formatName} maxLength={120} onChange={(event) => setFormatName(event.target.value)} required autoFocus /></label>
          <label className="field">Format JSON<textarea value={formatJson} onChange={(event) => setFormatJson(event.target.value)} required /></label>
          <div className="modal__actions">
            <button className="button button--ghost" type="button" onClick={() => formatImportDialog.current?.close()} disabled={working}>Cancel</button>
            <button className="button button--dark" type="submit" disabled={working || !formatName.trim() || !formatJson.trim()}>{working ? "Saving…" : "Import and save"}</button>
          </div>
        </form>
      </dialog>

      <dialog className="modal" ref={overwriteDialog} onClick={(event) => {
        if (event.target === event.currentTarget && !working) event.currentTarget.close();
      }}>
        <div className="modal__content">
          <button className="modal__close" type="button" onClick={() => overwriteDialog.current?.close()} aria-label="Close" disabled={working}>×</button>
          <span className="eyebrow">Existing format</span>
          <h2>Overwrite saved format?</h2>
          <p>You already have a format called <strong>{overwriteTarget?.name}</strong>. Do you want to overwrite it?</p>
          <div className="modal__actions">
            <button className="button button--ghost" type="button" onClick={() => overwriteDialog.current?.close()} disabled={working}>Cancel</button>
            <button className="button button--dark" type="button" onClick={() => overwriteTarget && void saveImportedFormat(overwriteTarget)} disabled={working}>{working ? "Overwriting…" : "Overwrite format"}</button>
          </div>
        </div>
      </dialog>

      <dialog className="modal" ref={deleteDialog} onClose={() => setDeleteTarget(null)} onClick={(event) => {
        if (event.target === event.currentTarget && !working) event.currentTarget.close();
      }}>
        <div className="modal__content">
          <button className="modal__close" type="button" onClick={() => deleteDialog.current?.close()} aria-label="Close" disabled={working}>×</button>
          <span className="eyebrow">Permanent deletion</span>
          <h2>Delete {deleteTarget?.kind === "format" ? "saved format" : "asset"}?</h2>
          <p>Are you sure you want to permanently delete <strong>{deleteName}</strong>? This cannot be undone.</p>
          <div className="modal__actions">
            <button className="button button--ghost" type="button" onClick={() => deleteDialog.current?.close()} disabled={working}>Cancel</button>
            <button className="button button--danger" type="button" onClick={() => void confirmDelete()} disabled={working}>{working ? "Deleting…" : "Delete permanently"}</button>
          </div>
        </div>
      </dialog>
    </main>
  );
}

function SavedAssetGroup({ title, count, onUpload, children }: { title: string; count: number; onUpload: () => void; children: ReactNode }) {
  return (
    <section className="saved-asset-group">
      <div className="saved-asset-group__heading">
        <div><h3>{title}</h3><p>{count} of 10 saved</p></div>
        <button className="button button--outline" type="button" onClick={onUpload} disabled={count >= 10}>+ Upload</button>
      </div>
      <div className="saved-asset-list">
        {count ? children : <p className="saved-data-empty">No saved {title.toLocaleLowerCase()}.</p>}
      </div>
    </section>
  );
}

function SavedAssetRow({ name, detail, busy, preview, onDelete }: { name: string; detail: string; busy: boolean; preview: ReactNode; onDelete: () => void }) {
  return (
    <article className="saved-asset-row">
      {preview}
      <div><strong>{name}</strong><small>{detail}</small></div>
      <button className="icon-button icon-button--danger" type="button" onClick={onDelete} disabled={busy} aria-label={`Delete ${name}`} title={`Delete ${name}`}><TrashIcon /></button>
    </article>
  );
}

function AssetImagePreview({ url, name, transparent = false }: { url?: string; name: string; transparent?: boolean }) {
  return <span className={`saved-asset-preview saved-asset-preview--image${transparent ? " saved-asset-preview--transparent" : ""}`}>{url ? <img src={url} alt={`${name} preview`} /> : <span aria-label="Loading preview">…</span>}</span>;
}

function SavedFontPreview({ id, url }: { id: string; url?: string }) {
  const [family, setFamily] = useState("");
  useEffect(() => {
    if (!url) { setFamily(""); return; }
    const fontFamily = `saved-font-${id.replace(/[^a-z0-9]/gi, "-")}`;
    const face = new FontFace(fontFamily, `url(${JSON.stringify(url)})`);
    let current = true;
    face.load().then((loaded) => {
      if (!current) return;
      document.fonts.add(loaded);
      setFamily(fontFamily);
    }).catch(() => { if (current) setFamily(""); });
    return () => {
      current = false;
      document.fonts.delete(face);
    };
  }, [id, url]);
  return <span className="saved-asset-preview saved-asset-preview--font" style={family ? { fontFamily: family } : undefined}>Aa</span>;
}

function FavoriteSinglesSection({ favorites, visible, fighters, onAdd, onChange, onSetPrimary, selected }: { favorites: FavoritesData; visible: FavoriteSinglesEntrant[]; fighters: FighterOption[]; onAdd: () => void; onChange: (favorites: FavoriteSinglesEntrant[]) => void; onSetPrimary: (id: string, primary: boolean) => void; selected: boolean }) {
  return (
    <section className="favorite-subsection">
      <div className="section-heading section-heading--compact">
        <div><h3>Favorite singles entrants</h3><p>{visible.length} shown</p></div>
        <button type="button" className="button-primary" onClick={onAdd}>Add singles entrant</button>
      </div>
      <div className="favorites-list">
        {visible.length ? visible.map((favorite) => (
          <article className="favorite-editor" key={favorite.id}>
            <div className="favorite-editor__heading">
              <strong>{favorite.tag || "Untitled entrant"}</strong>
              <CharacterStockIcons characters={favorite.characters} />
              <button type="button" className="button-danger" onClick={() => onChange(favorites.singles.filter((item) => item.id !== favorite.id))}>Remove</button>
            </div>
            <EntrantCharacterEditor tag={favorite.tag} characters={favorite.characters} fighters={fighters} onTagChange={(tag) => onChange(favorites.singles.map((item) => item.id === favorite.id ? { ...item, tag } : item))} onChange={(characters) => onChange(favorites.singles.map((item) => item.id === favorite.id ? { ...item, characters } : item))} />
            <label className="favorite-alias-field">
              Alternate spellings
              <input defaultValue={favorite.aliases.join(", ")} onBlur={(event) => onChange(favorites.singles.map((item) => item.id === favorite.id ? { ...item, aliases: parseAlternateSpellings(event.target.value) } : item))} placeholder="e.g. BUSTA, BU$TA" title="Example: BUSTA, BU$TA" />
              <small>Enter comma-separated alternate spellings, such as BUSTA, BU$TA. Sponsors are ignored while matching.</small>
            </label>
            <label className="choice"><input type="checkbox" checked={favorite.primary} onChange={(event) => onSetPrimary(favorite.id, event.target.checked)} /> Primary favorite for this tag</label>
            <p>{characterSummary(favorite.characters)}</p>
          </article>
        )) : <p className="form-message">{selected ? "This filter does not select a singles entrant." : "Add a singles entrant here, or save one from a placement card."}</p>}
      </div>
    </section>
  );
}

function FavoriteDoublesSection({ favorites, visible, fighters, onAdd, onChange, onReplaceMember, selected }: { favorites: FavoritesData; visible: FavoriteDoublesTeam[]; fighters: FighterOption[]; onAdd: () => void; onChange: (favorites: FavoriteDoublesTeam[]) => void; onReplaceMember: (teamId: string, member: "entrant_1" | "entrant_2", favorite: FavoriteSinglesEntrant) => void; selected: boolean }) {
  return (
    <section className="favorite-subsection">
      <div className="section-heading section-heading--compact">
        <div><h3>Favorite doubles teams</h3><p>{visible.length} shown</p></div>
        <button type="button" className="button-primary" onClick={onAdd}>Add doubles team</button>
      </div>
      <div className="favorites-list">
        {visible.length ? visible.map((team) => (
          <article className="favorite-editor" key={team.id}>
            <div className="favorite-editor__heading">
              <strong>{team.team_name || "Untitled team"}</strong>
              <button type="button" className="button-danger" onClick={() => onChange(favorites.doubles.filter((item) => item.id !== team.id))}>Remove</button>
            </div>
            <div className="row-fields">
              <label>Team name<input value={team.team_name} onChange={(event) => onChange(favorites.doubles.map((item) => item.id === team.id ? { ...item, team_name: event.target.value } : item))} /></label>
              <label>Team color<select value={team.team_color || "random"} onChange={(event) => onChange(favorites.doubles.map((item) => item.id === team.id ? { ...item, team_color: event.target.value } : item))}><option value="random">Random</option><option value="red">Red</option><option value="green">Green</option><option value="blue">Blue</option></select></label>
            </div>
            <div className="row-fields">
              <FavoriteTeamMember team={team} member="entrant_1" label="Entrant 1" favorites={favorites} fighters={fighters} onChange={onChange} onReplace={onReplaceMember} />
              <FavoriteTeamMember team={team} member="entrant_2" label="Entrant 2" favorites={favorites} fighters={fighters} onChange={onChange} onReplace={onReplaceMember} />
            </div>
          </article>
        )) : <p className="form-message">{selected ? "This filter does not select a doubles team." : "Add a doubles team here, or save one from a placement card."}</p>}
      </div>
    </section>
  );
}

function FavoriteTeamMember({ team, member, label, favorites, fighters, onChange, onReplace }: { team: FavoriteDoublesTeam; member: "entrant_1" | "entrant_2"; label: string; favorites: FavoritesData; fighters: FighterOption[]; onChange: (favorites: FavoriteDoublesTeam[]) => void; onReplace: (teamId: string, member: "entrant_1" | "entrant_2", favorite: FavoriteSinglesEntrant) => void }) {
  const entrant = team[member];
  return (
    <div className="favorite-member-editor">
      <SinglesFavoritePicker favorites={favorites.singles} label={`Use favorited entrant for ${label.toLocaleLowerCase()}`} onChoose={(favorite) => onReplace(team.id, member, favorite)} />
      <EntrantCharacterEditor tag={entrant.tag} tagLabel={`${label} tag`} characters={entrant.characters} fighters={fighters} onTagChange={(tag) => onChange(favorites.doubles.map((item) => item.id === team.id ? { ...item, [member]: { ...item[member], tag } } : item))} onChange={(characters) => onChange(favorites.doubles.map((item) => item.id === team.id ? { ...item, [member]: { ...item[member], characters } } : item))} />
    </div>
  );
}
