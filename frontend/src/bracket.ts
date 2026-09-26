import { EventFormat } from "./format";
import { FavoriteCharacter, FavoritesData, favoriteForImport, resolvedFavoriteTag } from "./favorites";

export interface ImportedBracketCharacter {
  fighter: string;
  color: string;
  pose: string;
  mirrorHorizontally: boolean;
}

export interface ImportedBracketMember {
  tag: string;
  characters: ImportedBracketCharacter[];
}

export interface ImportedBracketEntrant {
  tag: string;
  seed: number | null;
  placement: number | null;
  characters: ImportedBracketCharacter[];
  members: ImportedBracketMember[];
}

export interface ImportedBracketTournament {
  title: string;
  date: string;
  entrants_count: number | null;
  subtitle: string;
  event: string;
  link: string;
  event_format: string;
}

export interface BracketImportResponse {
  provider: string;
  tournament: ImportedBracketTournament;
  entrants: ImportedBracketEntrant[];
}

export interface FavoriteImportCorrection {
  id: string;
  entrantIndex: number;
  memberIndex: number | null;
  bracketTag: string;
  favoriteTag: string;
  resolvedTag: string;
  favoriteCharacters: FavoriteCharacter[];
  accepted: boolean;
}

export interface BracketImportReview {
  source: BracketImportResponse;
  corrections: FavoriteImportCorrection[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function optionalNumber(value: unknown): number | null {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function character(value: unknown): ImportedBracketCharacter | null {
  if (!isRecord(value)) return null;
  const fighter = text(value.fighter || value.melee_fighter_name).trim();
  if (!fighter) return null;
  return {
    fighter,
    color: text(value.color),
    pose: text(value.pose),
    mirrorHorizontally: value.mirrorHorizontally === true,
  };
}

function characters(value: unknown): ImportedBracketCharacter[] {
  return Array.isArray(value) ? value.map(character).filter((item): item is ImportedBracketCharacter => item !== null) : [];
}

function member(value: unknown): ImportedBracketMember | null {
  if (!isRecord(value)) return null;
  const tag = text(value.tag || value.name || value.player_tag).trim();
  if (!tag) return null;
  return { tag, characters: characters(value.characters) };
}

export function normalizeBracketImport(value: unknown, entrantLimit: number): BracketImportResponse {
  if (!isRecord(value) || !isRecord(value.tournament) || !Array.isArray(value.entrants)) {
    throw new Error("The bracket response was not in the expected format.");
  }
  const tournament = value.tournament;
  const entrants = value.entrants.slice(0, entrantLimit).flatMap((item): ImportedBracketEntrant[] => {
    if (!isRecord(item)) return [];
    const tag = text(item.tag || item.name || item.player_tag).trim();
    if (!tag) return [];
    return [{
      tag,
      seed: optionalNumber(item.seed),
      placement: optionalNumber(item.placement),
      characters: characters(item.characters),
      members: Array.isArray(item.members) ? item.members.map(member).filter((entry): entry is ImportedBracketMember => entry !== null) : [],
    }];
  });
  if (!entrants.length) throw new Error("The bracket did not return any placed entrants.");
  return {
    provider: text(value.provider),
    tournament: {
      title: text(tournament.title || tournament.name),
      date: text(tournament.date),
      entrants_count: optionalNumber(tournament.entrants_count || tournament.entrant_count),
      subtitle: text(tournament.subtitle),
      event: text(tournament.event),
      link: text(tournament.link),
      event_format: text(tournament.event_format || tournament.format),
    },
    entrants,
  };
}

function correctionFor(
  entrantIndex: number,
  memberIndex: number | null,
  tag: string,
  importedCharacters: ImportedBracketCharacter[],
  favorites: FavoritesData,
): FavoriteImportCorrection | null {
  const favorite = favoriteForImport(favorites.singles, tag, importedCharacters);
  if (!favorite) return null;
  return {
    id: `${entrantIndex}:${memberIndex ?? "entrant"}:${favorite.id}`,
    entrantIndex,
    memberIndex,
    bracketTag: tag,
    favoriteTag: favorite.tag,
    resolvedTag: resolvedFavoriteTag(tag, favorite.tag),
    favoriteCharacters: favorite.characters.map((item) => ({ ...item })),
    accepted: true,
  };
}

export function buildBracketReview(
  source: BracketImportResponse,
  favorites: FavoritesData,
  eventFormat: EventFormat,
): BracketImportReview {
  const corrections = source.entrants.flatMap((entrant, entrantIndex) => {
    if (eventFormat === "singles") {
      const match = correctionFor(entrantIndex, null, entrant.tag, entrant.characters, favorites);
      return match ? [match] : [];
    }
    return entrant.members.flatMap((item, memberIndex) => {
      const match = correctionFor(entrantIndex, memberIndex, item.tag, item.characters, favorites);
      return match ? [match] : [];
    });
  });
  return { source, corrections };
}

export function resolvedBracketImport(review: BracketImportReview): BracketImportResponse {
  const entrants = review.source.entrants.map((entrant) => ({
    ...entrant,
    characters: entrant.characters.map((item) => ({ ...item })),
    members: entrant.members.map((item) => ({ ...item, characters: item.characters.map((character) => ({ ...character })) })),
  }));
  review.corrections.filter((correction) => correction.accepted).forEach((correction) => {
    const entrant = entrants[correction.entrantIndex];
    if (!entrant) return;
    const target = correction.memberIndex === null ? entrant : entrant.members[correction.memberIndex];
    if (!target) return;
    target.tag = correction.resolvedTag;
    target.characters = correction.favoriteCharacters.map((item) => ({ ...item }));
  });
  return { ...review.source, tournament: { ...review.source.tournament }, entrants };
}

