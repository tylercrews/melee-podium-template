export interface FavoriteCharacter {
  fighter: string;
  color: string;
  pose: string;
}

export interface FavoriteSinglesEntrant {
  id: string;
  tag: string;
  characters: FavoriteCharacter[];
}

export interface FavoriteDoublesTeam {
  id: string;
  team_name: string;
  team_color: string;
  entrant_1: Omit<FavoriteSinglesEntrant, "id">;
  entrant_2: Omit<FavoriteSinglesEntrant, "id">;
}

export interface FavoritesData {
  version: 1;
  singles: FavoriteSinglesEntrant[];
  doubles: FavoriteDoublesTeam[];
}

const FAVORITES_KEY = "melee-podium.favorites.v1";
const emptyFavorites = (): FavoritesData => ({ version: 1, singles: [], doubles: [] });
const newId = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

function isCharacter(value: unknown): value is FavoriteCharacter {
  return !!value && typeof value === "object" &&
    typeof (value as FavoriteCharacter).fighter === "string" &&
    typeof (value as FavoriteCharacter).color === "string" &&
    typeof (value as FavoriteCharacter).pose === "string";
}

function asMember(value: unknown): Omit<FavoriteSinglesEntrant, "id"> | undefined {
  if (!value || typeof value !== "object") return undefined;
  const member = value as Record<string, unknown>;
  if (typeof member.tag !== "string" || !Array.isArray(member.characters) || !member.characters.every(isCharacter)) return undefined;
  return { tag: member.tag, characters: member.characters };
}

export function normalizeFavorites(value: unknown): FavoritesData {
  if (!value || typeof value !== "object") throw new Error("Favorites must be an object.");
  const source = value as Record<string, unknown>;
  if (!Array.isArray(source.singles) || !Array.isArray(source.doubles)) throw new Error("Favorites must contain singles and doubles lists.");
  const singles = source.singles.flatMap((item) => {
    const member = asMember(item);
    return member ? [{ ...member, id: typeof (item as Record<string, unknown>).id === "string" ? (item as Record<string, unknown>).id as string : newId() }] : [];
  });
  const doubles = source.doubles.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const team = item as Record<string, unknown>;
    const entrant_1 = asMember(team.entrant_1);
    const entrant_2 = asMember(team.entrant_2);
    if (typeof team.team_name !== "string" || typeof team.team_color !== "string" || !entrant_1 || !entrant_2) return [];
    return [{ id: typeof team.id === "string" ? team.id : newId(), team_name: team.team_name, team_color: team.team_color, entrant_1, entrant_2 }];
  });
  return { version: 1, singles, doubles };
}

export function loadFavorites(): FavoritesData {
  try {
    const saved = window.localStorage.getItem(FAVORITES_KEY);
    return saved ? normalizeFavorites(JSON.parse(saved)) : emptyFavorites();
  } catch {
    return emptyFavorites();
  }
}

export function saveFavorites(favorites: FavoritesData): FavoritesData {
  const normalized = normalizeFavorites(favorites);
  window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(normalized));
  return normalized;
}

export function newFavoriteId(): string { return newId(); }

export function characterSummary(characters: FavoriteCharacter[]): string {
  return characters.map((character) => character.fighter || "Unknown fighter").join(", ");
}
