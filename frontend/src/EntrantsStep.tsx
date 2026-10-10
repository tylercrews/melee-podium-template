import { FormEvent, useEffect, useRef, useState } from "react";
import { FighterOption } from "./api";
import { DoublesEntrantDraft, EntrantDraft, EntrantMemberDraft, SinglesEntrantDraft } from "./creationData";
import EntrantCharacterEditor from "./EntrantCharacterEditor";
import FontSizeSlider from "./FontSizeSlider";
import { DoublesFavoritePicker, SinglesFavoritePicker } from "./FavoritePicker";
import { FavoriteDoublesTeam, FavoriteSinglesEntrant, FavoritesData, newFavoriteId, normalizedFavoriteTag, parseAlternateSpellings } from "./favorites";
import { EventFormat } from "./format";

interface EntrantsStepProps {
  value: EntrantDraft[];
  count: number;
  eventFormat: EventFormat;
  includeSeeding: boolean;
  complete: boolean;
  fighters: FighterOption[];
  favorites: FavoritesData;
  onChange: (value: EntrantDraft[]) => void;
  onFavoritesChange: (value: FavoritesData) => void;
  onProceed: () => void;
}

function ordinal(value: number): string {
  const suffix = value % 100 >= 11 && value % 100 <= 13 ? "th" : value % 10 === 1 ? "st" : value % 10 === 2 ? "nd" : value % 10 === 3 ? "rd" : "th";
  return `${value}${suffix} Place`;
}

function favoriteMember(favorite: FavoriteSinglesEntrant): EntrantMemberDraft {
  return { tag: favorite.tag, characters: favorite.characters.map((character) => ({ ...character })), xHandle: "", country: "" };
}

export default function EntrantsStep({ value, count, eventFormat, includeSeeding, complete, fighters, favorites, onChange, onFavoritesChange, onProceed }: EntrantsStepProps) {
  const sectionRef = useRef<HTMLElement>(null);
  const favoriteDialogRef = useRef<HTMLDialogElement>(null);
  const [showErrors, setShowErrors] = useState(false);
  const [favoriteTarget, setFavoriteTarget] = useState<{ index: number; kind: "singles" | "doubles" } | null>(null);
  const [favoriteTag, setFavoriteTag] = useState("");
  const [alternateSpellings, setAlternateSpellings] = useState("");
  const [secondAlternateSpellings, setSecondAlternateSpellings] = useState("");
  const [primaryFavorite, setPrimaryFavorite] = useState(false);
  const displayed = value.slice(0, count);
  const update = (index: number, entrant: EntrantDraft) => onChange(value.map((item, current) => current === index ? entrant : item));
  const findSinglesFavorite = (tag: string) => favorites.singles.find((favorite) => [favorite.tag, ...favorite.aliases].some((candidate) => normalizedFavoriteTag(candidate) === normalizedFavoriteTag(tag)));

  function applySinglesFavorite(index: number, favorite: FavoriteSinglesEntrant) {
    const entrant = value[index];
    if (entrant?.kind !== "singles") return;
    update(index, { ...entrant, ...favoriteMember(favorite) });
  }

  function applyMemberFavorite(index: number, side: "entrant1" | "entrant2", favorite: FavoriteSinglesEntrant) {
    const entrant = value[index];
    if (entrant?.kind !== "doubles") return;
    update(index, { ...entrant, [side]: { ...favoriteMember(favorite), nameFontSizeAdjustment: entrant[side].nameFontSizeAdjustment } });
  }

  function applyTeamFavorite(index: number, favorite: FavoriteDoublesTeam) {
    const entrant = value[index];
    if (entrant?.kind !== "doubles") return;
    update(index, {
      ...entrant,
      teamName: favorite.team_name,
      teamColor: favorite.team_color,
      entrant1: { tag: favorite.entrant_1.tag, characters: favorite.entrant_1.characters.map((character) => ({ ...character })), xHandle: "", country: "", nameFontSizeAdjustment: entrant.entrant1.nameFontSizeAdjustment },
      entrant2: { tag: favorite.entrant_2.tag, characters: favorite.entrant_2.characters.map((character) => ({ ...character })), xHandle: "", country: "", nameFontSizeAdjustment: entrant.entrant2.nameFontSizeAdjustment },
    });
  }

  function openFavoriteDialog(index: number, entrant: EntrantDraft) {
    if (entrant.kind === "singles") {
      const existing = findSinglesFavorite(entrant.tag);
      setFavoriteTarget({ index, kind: "singles" });
      setFavoriteTag(existing?.tag ?? entrant.tag);
      setAlternateSpellings(existing?.aliases.join(", ") ?? "");
      setSecondAlternateSpellings("");
      setPrimaryFavorite(existing?.primary ?? false);
    } else {
      const existing = favorites.doubles.find((favorite) => favorite.team_name.trim().toLocaleLowerCase() === entrant.teamName.trim().toLocaleLowerCase());
      setFavoriteTarget({ index, kind: "doubles" });
      setFavoriteTag(existing?.team_name ?? entrant.teamName);
      setAlternateSpellings(existing?.entrant_1.aliases.join(", ") ?? "");
      setSecondAlternateSpellings(existing?.entrant_2.aliases.join(", ") ?? "");
      setPrimaryFavorite(false);
    }
    favoriteDialogRef.current?.showModal();
  }

  function saveFavorite(event: FormEvent) {
    event.preventDefault();
    if (!favoriteTarget) return;
    const entrant = value[favoriteTarget.index];
    if (!entrant || entrant.kind !== favoriteTarget.kind) return;
    if (entrant.kind === "singles") {
      const existing = findSinglesFavorite(entrant.tag);
      const next: FavoriteSinglesEntrant = {
        id: existing?.id ?? newFavoriteId(),
        tag: favoriteTag.trim(),
        aliases: parseAlternateSpellings(alternateSpellings),
        characters: entrant.characters.map((character) => ({ ...character })),
        primary: primaryFavorite,
      };
      const singles = existing
        ? favorites.singles.map((favorite) => favorite.id === existing.id ? next : primaryFavorite && normalizedFavoriteTag(favorite.tag) === normalizedFavoriteTag(next.tag) ? { ...favorite, primary: false } : favorite)
        : [...favorites.singles.map((favorite) => primaryFavorite && normalizedFavoriteTag(favorite.tag) === normalizedFavoriteTag(next.tag) ? { ...favorite, primary: false } : favorite), next];
      onFavoritesChange({ ...favorites, singles });
    } else {
      const existing = favorites.doubles.find((favorite) => favorite.team_name.trim().toLocaleLowerCase() === entrant.teamName.trim().toLocaleLowerCase());
      const next: FavoriteDoublesTeam = {
        id: existing?.id ?? newFavoriteId(),
        team_name: favoriteTag.trim(),
        team_color: entrant.teamColor,
        entrant_1: { tag: entrant.entrant1.tag, aliases: parseAlternateSpellings(alternateSpellings), characters: entrant.entrant1.characters.map((character) => ({ ...character })) },
        entrant_2: { tag: entrant.entrant2.tag, aliases: parseAlternateSpellings(secondAlternateSpellings), characters: entrant.entrant2.characters.map((character) => ({ ...character })) },
      };
      onFavoritesChange({ ...favorites, doubles: existing ? favorites.doubles.map((favorite) => favorite.id === existing.id ? next : favorite) : [...favorites.doubles, next] });
    }
    favoriteDialogRef.current?.close();
  }

  function validateOrGenerate() {
    if (complete) {
      window.dispatchEvent(new Event("format-preview:download"));
      onProceed();
      return;
    }
    setShowErrors(true);
    window.requestAnimationFrame(() => {
      const firstMissing = sectionRef.current?.querySelector<HTMLInputElement>("input:invalid");
      firstMissing?.scrollIntoView({ behavior: "smooth", block: "center" });
      firstMissing?.focus({ preventScroll: true });
    });
  }

  useEffect(() => {
    const handleFinishRequest = () => validateOrGenerate();
    window.addEventListener("entrants:finish", handleFinishRequest);
    return () => window.removeEventListener("entrants:finish", handleFinishRequest);
  });

  const favoriteEntrant = favoriteTarget ? value[favoriteTarget.index] : null;

  return <section className={`step-content entrants-step${showErrors ? " entrants-step--show-errors" : ""}`} ref={sectionRef}>
    <div className="step-intro"><div className="step-heading-row"><h1>{eventFormat === "singles" ? `Top ${count} Entrants` : `Top ${count} Teams`}</h1><button className="button button--ghost" type="button" onClick={validateOrGenerate}>{complete ? "Download Full Resolution Image" : "Finish filling out entrant information."}</button></div><p>Review imported results or enter each placement manually. Character colors and poses come from the renderer.</p></div>
    <div className="entrant-grid entrant-grid--maker">{displayed.map((entrant, index) => <fieldset className="entrant-card entrant-card--maker" key={`${entrant.kind}-${index}`}>
      <legend>{ordinal(entrant.placement)}</legend>
      {entrant.kind === "singles" ? <>
        <SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applySinglesFavorite(index, favorite)} />
        <FontSizeSlider label="Player name size adjustment" value={entrant.nameFontSizeAdjustment ?? 0} onChange={(nameFontSizeAdjustment) => update(index, { ...entrant, nameFontSizeAdjustment })} />
        {includeSeeding && <label>Seed<input type="number" min="1" value={entrant.seed} onChange={(event) => update(index, { ...entrant, seed: event.target.value })} required /></label>}
        <EntrantCharacterEditor tag={entrant.tag} tagPlaceholder={`Player ${index + 1}`} characters={entrant.characters} fighters={fighters} onTagChange={(tag) => update(index, { ...entrant, tag })} onChange={(characters) => update(index, { ...entrant, characters })} />
        <button className="button button--outline entrant-favorite-button" type="button" onClick={() => openFavoriteDialog(index, entrant)}>{findSinglesFavorite(entrant.tag) ? "Update Favorited Entrant" : "Save As Favorited Entrant"}</button>
      </> : <>
        <DoublesFavoritePicker favorites={favorites.doubles} onChoose={(favorite) => applyTeamFavorite(index, favorite)} />
        <FontSizeSlider label="Team name size adjustment" value={entrant.teamNameFontSizeAdjustment ?? 0} onChange={(teamNameFontSizeAdjustment) => update(index, { ...entrant, teamNameFontSizeAdjustment })} />
        <FontSizeSlider label="Player 1 name size adjustment" value={entrant.entrant1.nameFontSizeAdjustment ?? 0} onChange={(nameFontSizeAdjustment) => update(index, { ...entrant, entrant1: { ...entrant.entrant1, nameFontSizeAdjustment } })} />
        <FontSizeSlider label="Player 2 name size adjustment" value={entrant.entrant2.nameFontSizeAdjustment ?? 0} onChange={(nameFontSizeAdjustment) => update(index, { ...entrant, entrant2: { ...entrant.entrant2, nameFontSizeAdjustment } })} />
        <div className="entrant-team-fields"><label>Team name<input value={entrant.teamName} onChange={(event) => update(index, { ...entrant, teamName: event.target.value })} placeholder={`Team ${index + 1}`} required /></label>{includeSeeding && <label>Seed<input type="number" min="1" value={entrant.seed} onChange={(event) => update(index, { ...entrant, seed: event.target.value })} required /></label>}<label>Team color<select value={entrant.teamColor} onChange={(event) => update(index, { ...entrant, teamColor: event.target.value })}><option value="random">Random</option><option value="red">Red</option><option value="green">Green</option><option value="blue">Blue</option></select></label></div>
        <div className="entrant-team-members"><fieldset className="entrant-card entrant-member-card"><legend>Entrant 1</legend><SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applyMemberFavorite(index, "entrant1", favorite)} /><EntrantCharacterEditor tag={entrant.entrant1.tag} tagLabel="Entrant 1 tag" tagPlaceholder={`Player 1 · Team ${index + 1}`} characters={entrant.entrant1.characters} fighters={fighters} onTagChange={(tag) => update(index, { ...entrant, entrant1: { ...entrant.entrant1, tag } })} onChange={(characters) => update(index, { ...entrant, entrant1: { ...entrant.entrant1, characters } })} /></fieldset><fieldset className="entrant-card entrant-member-card"><legend>Entrant 2</legend><SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applyMemberFavorite(index, "entrant2", favorite)} /><EntrantCharacterEditor tag={entrant.entrant2.tag} tagLabel="Entrant 2 tag" tagPlaceholder={`Player 2 · Team ${index + 1}`} characters={entrant.entrant2.characters} fighters={fighters} onTagChange={(tag) => update(index, { ...entrant, entrant2: { ...entrant.entrant2, tag } })} onChange={(characters) => update(index, { ...entrant, entrant2: { ...entrant.entrant2, characters } })} /></fieldset></div>
        <button className="button button--outline entrant-favorite-button" type="button" onClick={() => openFavoriteDialog(index, entrant)}>{favorites.doubles.some((favorite) => favorite.team_name.trim().toLocaleLowerCase() === entrant.teamName.trim().toLocaleLowerCase()) ? "Update Favorited Team" : "Save As Favorited Team"}</button>
      </>}
    </fieldset>)}</div>
    <dialog className="modal favorite-save-modal" ref={favoriteDialogRef} onClose={() => setFavoriteTarget(null)} onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}><form className="modal__content" onSubmit={saveFavorite}><button className="modal__close" type="button" onClick={() => favoriteDialogRef.current?.close()} aria-label="Close">×</button><span className="eyebrow">Save reusable entrant data</span><h2>{favoriteTarget?.kind === "doubles" ? "Save favorited team" : "Save favorited entrant"}</h2><p>Review the output name and add alternate spellings that may appear in imported brackets.</p><label className="field">{favoriteTarget?.kind === "doubles" ? "Team name" : "Canonical output name"}<input value={favoriteTag} onChange={(event) => setFavoriteTag(event.target.value)} required /></label>{favoriteTarget?.kind === "singles" ? <><label className="field favorite-alternate-field">Alternate spellings<textarea value={alternateSpellings} onChange={(event) => setAlternateSpellings(event.target.value)} placeholder="BUSTA, BU$TA" /><small>Comma-separated spellings that should match this entrant. Sponsors and capitalization are ignored during matching.</small></label><label className="choice"><input type="checkbox" checked={primaryFavorite} onChange={(event) => setPrimaryFavorite(event.target.checked)} /> Use this as the primary favorite when multiple saved versions match</label></> : favoriteEntrant?.kind === "doubles" ? <div className="favorite-team-alternates"><label className="field favorite-alternate-field"><span>{favoriteEntrant.entrant1.tag} alternate spellings</span><textarea value={alternateSpellings} onChange={(event) => setAlternateSpellings(event.target.value)} placeholder="BUSTA, BU$TA" /><small>Comma-separated spellings for entrant 1.</small></label><label className="field favorite-alternate-field"><span>{favoriteEntrant.entrant2.tag} alternate spellings</span><textarea value={secondAlternateSpellings} onChange={(event) => setSecondAlternateSpellings(event.target.value)} placeholder="BUSTA, BU$TA" /><small>Comma-separated spellings for entrant 2.</small></label></div> : null}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => favoriteDialogRef.current?.close()}>Cancel</button><button className="button button--dark" type="submit">{favoriteTarget && ((favoriteTarget.kind === "singles" && findSinglesFavorite(favoriteEntrant?.kind === "singles" ? favoriteEntrant.tag : "")) || (favoriteTarget.kind === "doubles" && favorites.doubles.some((favorite) => favorite.team_name.trim().toLocaleLowerCase() === favoriteTag.trim().toLocaleLowerCase()))) ? "Update favorite" : "Save favorite"}</button></div></form></dialog>
  </section>;
}

