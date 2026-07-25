import { FavoriteDoublesTeam, FavoriteSinglesEntrant } from "./favorites";

const STOCK_COLOR_CODES: Record<string, string> = {
  default: "00",
  red: "01",
  green: "02",
  blue: "03",
  black: "04",
  white: "05",
  yellow: "06",
  pink: "07",
  purple: "09",
  cyan: "10",
};

export function stockIconPath(fighter: string, color = ""): string {
  const slug = fighter.toLowerCase().replace(/\./g, "").replace(/\s+/g, "_");
  const selectedColor = color.toLowerCase() || "default";
  const iconColor = STOCK_COLOR_CODES[selectedColor] ? selectedColor : "default";
  const colorCode = STOCK_COLOR_CODES[iconColor];
  return `${import.meta.env.BASE_URL}char_assets/stock_icons/${slug}/${colorCode}_${iconColor}_${slug}_stock.png`;
}

export function CharacterStockIcons({ characters }: { characters: { fighter: string; color?: string }[] }) {
  return <span className="stock-icons" aria-label={characters.map((item) => item.fighter).join(", ")}>
    {characters.filter((item) => item.fighter).map((character, index) => (
      <img key={`${character.fighter}-${index}`} src={stockIconPath(character.fighter, character.color)} alt={character.fighter} title={character.fighter} />
    ))}
  </span>;
}

export function SinglesFavoritePicker({ favorites, onChoose, label = "Use favorited entrant" }: { favorites: FavoriteSinglesEntrant[]; onChoose: (favorite: FavoriteSinglesEntrant) => void; label?: string }) {
  return <details className="favorite-picker">
    <summary>{label}</summary>
    <div className="favorite-menu">
      {favorites.length ? favorites.map((favorite) => {
        const character = favorite.characters[0];
        return <button type="button" className="favorite-choice" key={favorite.id} onClick={(event) => {
          onChoose(favorite);
          event.currentTarget.closest("details")?.removeAttribute("open");
        }}>
          <span>{favorite.tag || "Untitled entrant"}</span>
          <span aria-hidden="true">—</span>
          {character?.fighter ? <CharacterStockIcons characters={favorite.characters} /> : <span>Unknown fighter</span>}
        </button>;
      }) : <p className="form-message">No favorited entrants saved.</p>}
    </div>
  </details>;
}

export function DoublesFavoritePicker({ favorites, onChoose }: { favorites: FavoriteDoublesTeam[]; onChoose: (favorite: FavoriteDoublesTeam) => void }) {
  return <details className="favorite-picker">
    <summary>Use favorited doubles team</summary>
    <div className="favorite-menu">
      {favorites.length ? favorites.map((team) => <button type="button" className="favorite-choice favorite-choice--team" key={team.id} onClick={(event) => {
        onChoose(team);
        event.currentTarget.closest("details")?.removeAttribute("open");
      }}>
        <strong>{team.team_name || "Untitled team"}</strong>
        <span className="favorite-team-member"><span>{team.entrant_1.tag || "Entrant 1"}</span><span aria-hidden="true">—</span><CharacterStockIcons characters={team.entrant_1.characters} /></span>
        <span className="favorite-team-member"><span>{team.entrant_2.tag || "Entrant 2"}</span><span aria-hidden="true">—</span><CharacterStockIcons characters={team.entrant_2.characters} /></span>
      </button>) : <p className="form-message">No favorited doubles teams saved.</p>}
    </div>
  </details>;
}