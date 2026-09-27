import { FighterOption } from "./api";
import { DoublesEntrantDraft, EntrantDraft, EntrantMemberDraft, SinglesEntrantDraft } from "./creationData";
import EntrantCharacterEditor from "./EntrantCharacterEditor";
import { DoublesFavoritePicker, SinglesFavoritePicker } from "./FavoritePicker";
import { FavoriteDoublesTeam, FavoriteSinglesEntrant, FavoritesData, newFavoriteId, normalizedFavoriteTag } from "./favorites";
import { EventFormat } from "./format";

interface EntrantsStepProps {
  value: EntrantDraft[];
  count: number;
  eventFormat: EventFormat;
  includeSeeding: boolean;
  fighters: FighterOption[];
  favorites: FavoritesData;
  onChange: (value: EntrantDraft[]) => void;
  onFavoritesChange: (value: FavoritesData) => void;
}

function ordinal(value: number): string {
  const suffix = value % 100 >= 11 && value % 100 <= 13 ? "th" : value % 10 === 1 ? "st" : value % 10 === 2 ? "nd" : value % 10 === 3 ? "rd" : "th";
  return `${value}${suffix} Place`;
}

function favoriteMember(favorite: FavoriteSinglesEntrant): EntrantMemberDraft {
  return { tag: favorite.tag, characters: favorite.characters.map((character) => ({ ...character })), xHandle: "", country: "" };
}

export default function EntrantsStep({ value, count, eventFormat, includeSeeding, fighters, favorites, onChange, onFavoritesChange }: EntrantsStepProps) {
  const displayed = value.slice(0, count);
  const update = (index: number, entrant: EntrantDraft) => onChange(value.map((item, current) => current === index ? entrant : item));

  function applySinglesFavorite(index: number, favorite: FavoriteSinglesEntrant) {
    const entrant = value[index];
    if (entrant?.kind !== "singles") return;
    update(index, { ...entrant, ...favoriteMember(favorite) });
  }

  function applyMemberFavorite(index: number, side: "entrant1" | "entrant2", favorite: FavoriteSinglesEntrant) {
    const entrant = value[index];
    if (entrant?.kind !== "doubles") return;
    update(index, { ...entrant, [side]: favoriteMember(favorite) });
  }

  function applyTeamFavorite(index: number, favorite: FavoriteDoublesTeam) {
    const entrant = value[index];
    if (entrant?.kind !== "doubles") return;
    update(index, {
      ...entrant,
      teamName: favorite.team_name,
      teamColor: favorite.team_color,
      entrant1: { tag: favorite.entrant_1.tag, characters: favorite.entrant_1.characters.map((character) => ({ ...character })), xHandle: "", country: "" },
      entrant2: { tag: favorite.entrant_2.tag, characters: favorite.entrant_2.characters.map((character) => ({ ...character })), xHandle: "", country: "" },
    });
  }

  function toggleSinglesFavorite(entrant: SinglesEntrantDraft, checked: boolean) {
    const existing = favorites.singles.find((favorite) => normalizedFavoriteTag(favorite.tag) === normalizedFavoriteTag(entrant.tag));
    if (!checked) {
      onFavoritesChange({ ...favorites, singles: favorites.singles.filter((favorite) => favorite.id !== existing?.id) });
      return;
    }
    const next: FavoriteSinglesEntrant = { id: existing?.id ?? newFavoriteId(), tag: entrant.tag, aliases: existing?.aliases ?? [], characters: entrant.characters.map((character) => ({ ...character })), primary: existing?.primary ?? false };
    onFavoritesChange({ ...favorites, singles: existing ? favorites.singles.map((favorite) => favorite.id === existing.id ? next : favorite) : [...favorites.singles, next] });
  }

  function toggleDoublesFavorite(entrant: DoublesEntrantDraft, checked: boolean) {
    const existing = favorites.doubles.find((favorite) => favorite.team_name.trim().toLocaleLowerCase() === entrant.teamName.trim().toLocaleLowerCase());
    if (!checked) {
      onFavoritesChange({ ...favorites, doubles: favorites.doubles.filter((favorite) => favorite.id !== existing?.id) });
      return;
    }
    const next: FavoriteDoublesTeam = {
      id: existing?.id ?? newFavoriteId(),
      team_name: entrant.teamName,
      team_color: entrant.teamColor,
      entrant_1: { tag: entrant.entrant1.tag, aliases: existing?.entrant_1.aliases ?? [], characters: entrant.entrant1.characters.map((character) => ({ ...character })) },
      entrant_2: { tag: entrant.entrant2.tag, aliases: existing?.entrant_2.aliases ?? [], characters: entrant.entrant2.characters.map((character) => ({ ...character })) },
    };
    onFavoritesChange({ ...favorites, doubles: existing ? favorites.doubles.map((favorite) => favorite.id === existing.id ? next : favorite) : [...favorites.doubles, next] });
  }

  return <section className="step-content entrants-step">
    <div className="step-intro"><h1>{eventFormat === "singles" ? `Top ${count} Entrants` : `Top ${count} Teams`}</h1><p>Review imported results or enter each placement manually. Character colors and poses come from the renderer.</p></div>
    <div className="entrant-grid entrant-grid--maker">{displayed.map((entrant, index) => <fieldset className="entrant-card entrant-card--maker" key={`${entrant.kind}-${index}`}>
      <legend>{ordinal(entrant.placement)}</legend>
      {entrant.kind === "singles" ? <>
        <SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applySinglesFavorite(index, favorite)} />
        {includeSeeding && <label>Seed<input type="number" min="1" value={entrant.seed} onChange={(event) => update(index, { ...entrant, seed: event.target.value })} /></label>}
        <EntrantCharacterEditor tag={entrant.tag} tagPlaceholder={`Player ${index + 1}`} characters={entrant.characters} fighters={fighters} onTagChange={(tag) => update(index, { ...entrant, tag })} onChange={(characters) => update(index, { ...entrant, characters })} />
        <label className="choice"><input type="checkbox" checked={favorites.singles.some((favorite) => normalizedFavoriteTag(favorite.tag) === normalizedFavoriteTag(entrant.tag))} onChange={(event) => toggleSinglesFavorite(entrant, event.target.checked)} /> Save or update favorite entrant</label>
      </> : <>
        <DoublesFavoritePicker favorites={favorites.doubles} onChoose={(favorite) => applyTeamFavorite(index, favorite)} />
        <div className="entrant-team-fields"><label>Team name<input value={entrant.teamName} onChange={(event) => update(index, { ...entrant, teamName: event.target.value })} placeholder={`Team ${index + 1}`} required /></label>{includeSeeding && <label>Seed<input type="number" min="1" value={entrant.seed} onChange={(event) => update(index, { ...entrant, seed: event.target.value })} /></label>}<label>Team color<select value={entrant.teamColor} onChange={(event) => update(index, { ...entrant, teamColor: event.target.value })}><option value="random">Random</option><option value="red">Red</option><option value="green">Green</option><option value="blue">Blue</option></select></label></div>
        <div className="entrant-team-members"><fieldset className="entrant-card entrant-member-card"><legend>Entrant 1</legend><SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applyMemberFavorite(index, "entrant1", favorite)} /><EntrantCharacterEditor tag={entrant.entrant1.tag} tagLabel="Entrant 1 tag" tagPlaceholder={`Player 1 · Team ${index + 1}`} characters={entrant.entrant1.characters} fighters={fighters} onTagChange={(tag) => update(index, { ...entrant, entrant1: { ...entrant.entrant1, tag } })} onChange={(characters) => update(index, { ...entrant, entrant1: { ...entrant.entrant1, characters } })} /></fieldset><fieldset className="entrant-card entrant-member-card"><legend>Entrant 2</legend><SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applyMemberFavorite(index, "entrant2", favorite)} /><EntrantCharacterEditor tag={entrant.entrant2.tag} tagLabel="Entrant 2 tag" tagPlaceholder={`Player 2 · Team ${index + 1}`} characters={entrant.entrant2.characters} fighters={fighters} onTagChange={(tag) => update(index, { ...entrant, entrant2: { ...entrant.entrant2, tag } })} onChange={(characters) => update(index, { ...entrant, entrant2: { ...entrant.entrant2, characters } })} /></fieldset></div>
        <label className="choice"><input type="checkbox" checked={favorites.doubles.some((favorite) => favorite.team_name.trim().toLocaleLowerCase() === entrant.teamName.trim().toLocaleLowerCase())} onChange={(event) => toggleDoublesFavorite(entrant, event.target.checked)} /> Save or update favorite doubles team</label>
      </>}
    </fieldset>)}</div>
  </section>;
}

