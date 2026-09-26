export interface FavoriteCharacter {
  fighter: string;
  color: string;
  pose: string;
  mirrorHorizontally: boolean;
}

export interface FavoriteSinglesEntrant {
  id: string;
  tag: string;
  aliases: string[];
  characters: FavoriteCharacter[];
  primary: boolean;
}

export interface FavoriteDoublesTeam {
  id: string;
  team_name: string;
  team_color: string;
  entrant_1: Omit<FavoriteSinglesEntrant, "id" | "primary">;
  entrant_2: Omit<FavoriteSinglesEntrant, "id" | "primary">;
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
    typeof (value as FavoriteCharacter).pose === "string" &&
    ((value as Partial<FavoriteCharacter>).mirrorHorizontally === undefined ||
      typeof (value as FavoriteCharacter).mirrorHorizontally === "boolean");
}

function normalizeCharacter(character: FavoriteCharacter): FavoriteCharacter {
  return { ...character, mirrorHorizontally: character.mirrorHorizontally === true };
}

function asMember(value: unknown): Omit<FavoriteSinglesEntrant, "id" | "primary"> | undefined {
  if (!value || typeof value !== "object") return undefined;
  const member = value as Record<string, unknown>;
  if (typeof member.tag !== "string" || !Array.isArray(member.characters) || !member.characters.every(isCharacter)) return undefined;
  const aliases = Array.isArray(member.aliases)
    ? member.aliases.filter((alias): alias is string => typeof alias === "string").map((alias) => alias.trim()).filter(Boolean)
    : [];
  return { tag: member.tag, aliases: [...new Set(aliases)], characters: member.characters.map(normalizeCharacter) };
}

function isPrimary(value: unknown): boolean {
  return value === true;
}

export function normalizeFavorites(value: unknown): FavoritesData {
  if (!value || typeof value !== "object") throw new Error("Favorites must be an object.");
  const source = value as Record<string, unknown>;
  if (!Array.isArray(source.singles) || !Array.isArray(source.doubles)) throw new Error("Favorites must contain singles and doubles lists.");
  const singles = source.singles.flatMap((item) => {
    const member = asMember(item);
    return member ? [{ ...member, id: typeof (item as Record<string, unknown>).id === "string" ? (item as Record<string, unknown>).id as string : newId(), primary: isPrimary((item as Record<string, unknown>).primary) }] : [];
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

export function normalizedFavoriteTag(tag: string): string {
  return entrantIdentity(tag).toLocaleLowerCase().replace(/\s+/g, " ");
}

export function splitEntrantTag(tag: string): { sponsor: string; identity: string } {
  const parts = tag.split("|").map((part) => part.trim()).filter(Boolean);
  if (parts.length < 2) return { sponsor: "", identity: tag.trim() };
  return { sponsor: parts.slice(0, -1).join(" | "), identity: parts[parts.length - 1] ?? "" };
}

export function entrantIdentity(tag: string): string {
  return splitEntrantTag(tag).identity.normalize("NFKC").trim();
}

/** Use the favorite's canonical player tag while retaining a sponsor supplied by the bracket. */
export function resolvedFavoriteTag(bracketTag: string, favoriteTag: string): string {
  const bracket = splitEntrantTag(bracketTag);
  const favorite = splitEntrantTag(favoriteTag);
  const sponsor = bracket.sponsor || favorite.sponsor;
  return sponsor ? `${sponsor} | ${favorite.identity}` : favorite.identity;
}

function normalizedFighters(characters: { fighter: string }[]): string[] {
  return characters.map((character) => character.fighter.trim().toLowerCase()).filter(Boolean).sort();
}

/** Select the applicable favorite for a bracket import. */
export function favoriteForImport(
  favorites: FavoriteSinglesEntrant[],
  tag: string,
  importedCharacters: { fighter: string }[],
): FavoriteSinglesEntrant | undefined {
  const importedTag = normalizedFavoriteTag(tag);
  const tagMatches = favorites.filter((favorite) =>
    [favorite.tag, ...favorite.aliases].some((candidate) => normalizedFavoriteTag(candidate) === importedTag),
  );
  const importedFighters = normalizedFighters(importedCharacters);
  if (!importedFighters.length) return tagMatches.find((favorite) => favorite.primary) ?? tagMatches[0];

  return tagMatches.find((favorite) => {
    const favoriteFighters = normalizedFighters(favorite.characters);
    return favoriteFighters.length === importedFighters.length && favoriteFighters.every((fighter, index) => fighter === importedFighters[index]);
  }) ?? tagMatches.find((favorite) => favorite.primary) ?? tagMatches[0];
}

export function characterSummary(characters: FavoriteCharacter[]): string {
  return characters.map((character) => character.fighter || "Unknown fighter").join(", ");
}



