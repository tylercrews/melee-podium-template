import { FavoriteDoublesTeam, FavoriteSinglesEntrant, characterSummary } from "./favorites";

function stockIconPath(fighter: string): string {
  const slug = fighter.toLowerCase().replace(/\./g, "").replace(/\s+/g, "_");
  return `${import.meta.env.BASE_URL}char_assets/stock_icons/${slug}/00_default_${slug}_stock.png`;
}

export function CharacterStockIcons({ characters }: { characters: { fighter: string }[] }) {
  return <span className="stock-icons" aria-label={characters.map((item) => item.fighter).join(", ")}>
    {characters.filter((item) => item.fighter).map((character, index) => (
      <img key={`${character.fighter}-${index}`} src={stockIconPath(character.fighter)} alt={character.fighter} title={character.fighter} />
    ))}
  </span>;
}

export function SinglesFavoritePicker({ favorites, onChoose, label = "Use favorited entrant" }: { favorites: FavoriteSinglesEntrant[]; onChoose: (favorite: FavoriteSinglesEntrant) => void; label?: string }) {
  return <label>
    {label}
    <select value="" onChange={(event) => {
      const favorite = favorites.find((item) => item.id === event.target.value);
      if (favorite) onChoose(favorite);
    }}>
      <option value="">{favorites.length ? "Choose a favorite" : "No favorited entrants saved"}</option>
      {favorites.map((favorite) => <option key={favorite.id} value={favorite.id}>
        {favorite.tag || "Untitled entrant"} — {characterSummary(favorite.characters)}
      </option>)}
    </select>
  </label>;
}
export function DoublesFavoritePicker({ favorites, onChoose }: { favorites: FavoriteDoublesTeam[]; onChoose: (favorite: FavoriteDoublesTeam) => void }) {
  return <label>
    Use favorited doubles team
    <select value="" onChange={(event) => {
      const favorite = favorites.find((item) => item.id === event.target.value);
      if (favorite) onChoose(favorite);
    }}>
      <option value="">{favorites.length ? "Choose a favorite" : "No favorited doubles teams saved"}</option>
      {favorites.map((team) => <option key={team.id} value={team.id}>
        {team.team_name || "Untitled team"} — {team.entrant_1.tag || "Entrant 1"} &amp; {team.entrant_2.tag || "Entrant 2"}
      </option>)}
    </select>
  </label>;
}