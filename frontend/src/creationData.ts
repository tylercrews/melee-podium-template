import { BracketImportReview, resolvedBracketImport } from "./bracket";
import { FavoriteCharacter } from "./favorites";
import { EventFormat, MetadataField } from "./format";

export interface TournamentDetails {
  title: string;
  subtitle: string;
  event: string;
  date: string;
  entrantsCount: string;
  tournamentLink: string;
  streamLink: string;
  vodLink: string;
  toXAccount: string;
  toTwitchAccount: string;
  toBlueskyAccount: string;
  location: string;
}

export interface EntrantMemberDraft {
  tag: string;
  characters: FavoriteCharacter[];
  xHandle: string;
  country: string;
}

export interface SinglesEntrantDraft extends EntrantMemberDraft {
  kind: "singles";
  placement: number;
  seed: string;
  providerId: string;
}

export interface DoublesEntrantDraft {
  kind: "doubles";
  placement: number;
  seed: string;
  teamName: string;
  teamColor: string;
  entrant1: EntrantMemberDraft;
  entrant2: EntrantMemberDraft;
  providerId: string;
}

export type EntrantDraft = SinglesEntrantDraft | DoublesEntrantDraft;

const emptyCharacter = (): FavoriteCharacter => ({ fighter: "", color: "", pose: "", mirrorHorizontally: false });

export function emptyTournamentDetails(): TournamentDetails {
  return {
    title: "",
    subtitle: "",
    event: "",
    date: "",
    entrantsCount: "",
    tournamentLink: "",
    streamLink: "",
    vodLink: "",
    toXAccount: "",
    toTwitchAccount: "",
    toBlueskyAccount: "",
    location: "",
  };
}

export function mergeImportedTournament(current: TournamentDetails, review: BracketImportReview): TournamentDetails {
  const imported = review.source.tournament;
  return {
    ...current,
    title: imported.title || current.title,
    subtitle: imported.subtitle || current.subtitle,
    event: imported.event || current.event,
    date: /^\d{4}-\d{2}-\d{2}/.test(imported.date) ? imported.date.slice(0, 10) : current.date,
    entrantsCount: imported.entrants_count ? String(imported.entrants_count) : current.entrantsCount,
    tournamentLink: imported.link || current.tournamentLink,
    location: imported.location || current.location,
  };
}

export const METADATA_FIELD_DETAILS: Record<MetadataField, { label: string; key: keyof TournamentDetails; type?: "date" | "number" | "url"; placeholder: string }> = {
  event: { label: "Event", key: "event", placeholder: "Melee Singles" },
  date: { label: "Date", key: "date", type: "date", placeholder: "" },
  entrants_count: { label: "Entrant count", key: "entrantsCount", type: "number", placeholder: "64" },
  tournament_link: { label: "Tournament link", key: "tournamentLink", type: "url", placeholder: "https://start.gg/…" },
  stream_link: { label: "Stream link", key: "streamLink", type: "url", placeholder: "https://twitch.tv/…" },
  vod_link: { label: "VOD link", key: "vodLink", type: "url", placeholder: "https://youtube.com/…" },
  to_x_account: { label: "TO X account", key: "toXAccount", placeholder: "@tournament" },
  to_twitch_account: { label: "TO Twitch account", key: "toTwitchAccount", placeholder: "tournamentstream" },
  to_bluesky_account: { label: "TO Bluesky account", key: "toBlueskyAccount", placeholder: "tournament.bsky.social" },
};

export function isTournamentComplete(value: TournamentDetails, selectedFields: MetadataField[]): boolean {
  if (!value.title.trim()) return false;
  return selectedFields.every((field) => {
    const fieldValue = value[METADATA_FIELD_DETAILS[field].key];
    return field === "entrants_count" ? Number(fieldValue) > 0 : fieldValue.trim().length > 0;
  });
}

function placementForIndex(index: number, count: number): number {
  return count >= 8 ? [1, 2, 3, 4, 5, 5, 7, 7][index] ?? index + 1 : index + 1;
}

function emptyMember(): EntrantMemberDraft {
  return { tag: "", characters: [emptyCharacter()], xHandle: "", country: "" };
}

function emptyEntrant(index: number, count: number, eventFormat: EventFormat): EntrantDraft {
  const placement = placementForIndex(index, count);
  if (eventFormat === "singles") {
    return { kind: "singles", placement, seed: String(index + 1), providerId: "", ...emptyMember() };
  }
  return { kind: "doubles", placement, seed: String(index + 1), teamName: "", teamColor: "random", entrant1: emptyMember(), entrant2: emptyMember(), providerId: "" };
}

export function ensureEntrantDrafts(current: EntrantDraft[], count: number, eventFormat: EventFormat): EntrantDraft[] {
  const compatible = current.every((entrant) => entrant.kind === eventFormat);
  const retained = compatible ? [...current] : [];
  while (retained.length < count) retained.push(emptyEntrant(retained.length, count, eventFormat));
  return retained.map((entrant, index) => index < count ? { ...entrant, placement: placementForIndex(index, count) } : entrant);
}

function importedCharacters(characters: FavoriteCharacter[]): FavoriteCharacter[] {
  return characters.length ? characters.map((character) => ({ ...character })) : [emptyCharacter()];
}

export function entrantDraftsFromBracket(review: BracketImportReview, eventFormat: EventFormat): EntrantDraft[] {
  const imported = resolvedBracketImport(review);
  return imported.entrants.map((entrant, index) => {
    if (eventFormat === "singles") {
      return {
        kind: "singles",
        tag: entrant.tag,
        seed: entrant.seed ? String(entrant.seed) : "",
        placement: entrant.placement ?? index + 1,
        characters: importedCharacters(entrant.characters),
        xHandle: entrant.x_handle,
        country: entrant.country,
        providerId: entrant.provider_id,
      };
    }
    const first = entrant.members[0];
    const second = entrant.members[1];
    return {
      kind: "doubles",
      teamName: entrant.tag,
      teamColor: "random",
      seed: entrant.seed ? String(entrant.seed) : "",
      placement: entrant.placement ?? index + 1,
      entrant1: first ? { tag: first.tag, characters: importedCharacters(first.characters), xHandle: first.x_handle, country: first.country } : emptyMember(),
      entrant2: second ? { tag: second.tag, characters: importedCharacters(second.characters), xHandle: second.x_handle, country: second.country } : emptyMember(),
      providerId: entrant.provider_id,
    };
  });
}

function memberComplete(member: EntrantMemberDraft): boolean {
  return Boolean(member.tag.trim() && member.characters.length && member.characters.every((character) => character.fighter.trim()));
}

export function areEntrantsComplete(entrants: EntrantDraft[], count: number, eventFormat: EventFormat, includeSeeding: boolean): boolean {
  const visible = entrants.slice(0, count);
  if (visible.length !== count) return false;
  return visible.every((entrant) => {
    if (includeSeeding && !(Number(entrant.seed) > 0)) return false;
    return eventFormat === "singles"
      ? entrant.kind === "singles" && memberComplete(entrant)
      : entrant.kind === "doubles" && Boolean(entrant.teamName.trim()) && memberComplete(entrant.entrant1) && memberComplete(entrant.entrant2);
  });
}

