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

export function SinglesFavoritePicker({ favorites, onChoose, label = "Use a favorite entrant" }: { favorites: FavoriteSinglesEntrant[]; onChoose: (favorite: FavoriteSinglesEntrant) => void; label?: string }) {
  if (!favorites.length) return null;
  return <details className="favorite-picker"><summary>{label}</summary><div className="favorite-menu">
    {favorites.map((favorite) => <button type="button" className="favorite-choice" key={favorite.id} onClick={() => onChoose(favorite)}>
      <strong>{favorite.tag || "Untitled entrant"}</strong><CharacterStockIcons characters={favorite.characters} /><span>{characterSummary(favorite.characters)}</span>
    </button>)}
  </div></details>;
}

export function DoublesFavoritePicker({ favorites, onChoose }: { favorites: FavoriteDoublesTeam[]; onChoose: (favorite: FavoriteDoublesTeam) => void }) {
  if (!favorites.length) return null;
  return <details className="favorite-picker"><summary>Use a favorite doubles team</summary><div className="favorite-menu">
    {favorites.map((team) => <button type="button" className="favorite-choice favorite-choice--team" key={team.id} onClick={() => onChoose(team)}>
      <strong>{team.team_name || "Untitled team"}</strong>
      <span>{team.entrant_1.tag || "Entrant 1"} <CharacterStockIcons characters={team.entrant_1.characters} /></span>
      <span>{team.entrant_2.tag || "Entrant 2"} <CharacterStockIcons characters={team.entrant_2.characters} /></span>
    </button>)}
  </div></details>;
}
