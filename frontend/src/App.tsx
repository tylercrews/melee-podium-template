import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  FighterOption,
  getHealth,
  getStats,
  getOptions,
  importBracket,
  recordDownload,
  renderPodium,
} from "./api";
import { DoublesFavoritePicker, SinglesFavoritePicker } from "./FavoritePicker";
import EntrantCharacterEditor, { createCharacterForm } from "./EntrantCharacterEditor";
import Footer from "./Footer";
import FavoritesManagement from "./FavoritesManagement";
import { FavoriteDoublesTeam, FavoriteSinglesEntrant, FavoritesData, favoriteForImport, loadFavorites, newFavoriteId, saveFavorites } from "./favorites";

interface CharacterForm {
  fighter: string;
  color: string;
  pose: string;
  mirrorHorizontally: boolean;
}

interface EntrantForm {
  tag: string;
  characters: CharacterForm[];
}

interface SinglesEntrantForm {
  kind: "singles";
  tag: string;
  seed: string;
  characters: CharacterForm[];
}

interface DoublesTeamForm {
  kind: "doubles";
  team_name: string;
  seed: string;
  team_color: string;
  entrant_1: EntrantForm;
  entrant_2: EntrantForm;
}

type EntrantFormState = SinglesEntrantForm | DoublesTeamForm;

interface TournamentForm {
  title: string;
  date: string;
  entrantsCount: string;
  subtitle: string;
  event: string;
  link: string;
}

interface PodiumSelections {
  tournament: TournamentForm;
  eventFormat: EventFormat;
  podiumSize: PodiumSize;
  top8Layout: Top8Layout;
  includeSeeds: boolean;
  entrants: EntrantFormState[];
  bracketUrl: string;
}

const MELEE_FIGHTER_NAMES = [
  "Bowser", "Captain Falcon", "Donkey Kong", "Dr. Mario", "Falco", "Fox", "Ganondorf", "Ice Climbers", "Jigglypuff", "Kirby", "Link", "Luigi", "Mario", "Marth", "Mewtwo", "Mr. Game and Watch", "Ness", "Peach", "Pichu", "Pikachu", "Roy", "Samus", "Sheik", "Yoshi", "Young Link", "Zelda",
] as const;

const DEFAULT_FIGHTERS: FighterOption[] = MELEE_FIGHTER_NAMES.map((name) => ({ name, options: [] }));
type EventFormat = "singles" | "doubles";
type PodiumSize = 3 | 4 | 8;
type Top8Layout = "all_showing" | "four_podium";
type PodiumFont = "tyrowo" | "impact" | "ubuntu";

const PODIUM_SELECTIONS_KEY = "melee-podium.selections.v1";
const PREFERRED_FONT_KEY = "melee-podium.preferred-font.v1";

const PODIUM_FONTS: ReadonlyArray<{ value: PodiumFont; label: string }> = [
  { value: "tyrowo", label: "Tyrowo Inked" },
  { value: "impact", label: "Impact" },
  { value: "ubuntu", label: "Ubuntu" },
];
function createEntrantForm(existing?: EntrantForm): EntrantForm {
  return {
    tag: existing?.tag ?? "",
    characters: existing?.characters?.length
      ? existing.characters.map((character) => ({ ...character, mirrorHorizontally: character.mirrorHorizontally === true }))
      : [createCharacterForm()],
  };
}

function createSinglesEntrant(
  placement: number,
  existing?: SinglesEntrantForm,
): SinglesEntrantForm {
  return {
    kind: "singles",
    tag: existing?.tag ?? "",
    seed: existing?.seed ?? String(placement),
    characters: existing?.characters?.length
      ? existing.characters.map((character) => ({ ...character, mirrorHorizontally: character.mirrorHorizontally === true }))
      : [createCharacterForm()],
  };
}

function createDoublesTeam(
  placement: number,
  existing?: DoublesTeamForm | SinglesEntrantForm,
): DoublesTeamForm {
  const fallbackEntrant =
    existing?.kind === "singles"
      ? createEntrantForm({
          tag: existing.tag,
          characters: existing.characters,
        })
      : undefined;

  return {
    kind: "doubles",
    team_name: existing?.kind === "doubles" ? existing.team_name : "",
    seed: existing?.kind === "doubles" ? existing.seed : String(placement),
    team_color: existing?.kind === "doubles" ? existing.team_color || "random" : "random",
    entrant_1:
      existing?.kind === "doubles"
        ? createEntrantForm(existing.entrant_1)
        : fallbackEntrant ?? createEntrantForm(),
    entrant_2:
      existing?.kind === "doubles"
        ? createEntrantForm(existing.entrant_2)
        : createEntrantForm(),
  };
}

function createEntrants(
  count: number,
  format: EventFormat,
  existing: EntrantFormState[] = [],
): EntrantFormState[] {
  return Array.from({ length: count }, (_, index) => {
    const placement = index + 1;
    const existingEntry = existing[index];

    if (format === "singles") {
      if (existingEntry?.kind === "singles") {
        return createSinglesEntrant(placement, existingEntry);
      }
      if (existingEntry?.kind === "doubles") {
        return createSinglesEntrant(placement, {
          kind: "singles",
          tag: existingEntry.entrant_1.tag,
          seed: existingEntry.seed,
          characters: existingEntry.entrant_1.characters,
        });
      }
      return createSinglesEntrant(placement);
    }

    if (existingEntry?.kind === "doubles") {
      return createDoublesTeam(placement, existingEntry);
    }

    if (existingEntry?.kind === "singles") {
      return createDoublesTeam(placement, existingEntry);
    }

    return createDoublesTeam(placement);
  });
}

function defaultTournament(): TournamentForm {
  return {
    title: "",
    date: new Date().toISOString().slice(0, 10),
    entrantsCount: "16",
    subtitle: "",
    event: "",
    link: "",
  };
}

function defaultPodiumSelections(): PodiumSelections {
  return {
    tournament: defaultTournament(),
    eventFormat: "singles",
    podiumSize: 8,
    top8Layout: "all_showing",
    includeSeeds: true,
    entrants: createEntrants(8, "singles"),
    bracketUrl: "",
  };
}

function isPodiumFont(value: unknown): value is PodiumFont {
  return value === "tyrowo" || value === "impact" || value === "ubuntu";
}

function loadPodiumSelections(): PodiumSelections {
  const defaults = defaultPodiumSelections();
  try {
    const saved = JSON.parse(window.localStorage.getItem(PODIUM_SELECTIONS_KEY) ?? "null");
    if (!isRecord(saved)) return defaults;
    const format: EventFormat = saved.eventFormat === "doubles" ? "doubles" : "singles";
    const size = saved.podiumSize === 3 || saved.podiumSize === 4 || saved.podiumSize === 8
      ? saved.podiumSize as PodiumSize
      : defaults.podiumSize;
    const top8Layout: Top8Layout = saved.top8Layout === "four_podium" ? "four_podium" : "all_showing";
    const sourceTournament = isRecord(saved.tournament) ? saved.tournament : {};
    const tournament: TournamentForm = {
      title: stringValue(sourceTournament.title),
      date: stringValue(sourceTournament.date) || defaults.tournament.date,
      entrantsCount: stringValue(sourceTournament.entrantsCount) || defaults.tournament.entrantsCount,
      subtitle: stringValue(sourceTournament.subtitle),
      event: stringValue(sourceTournament.event),
      link: stringValue(sourceTournament.link),
    };
    const savedEntrants = Array.isArray(saved.entrants) ? saved.entrants : [];
    const normalizedSize = format === "doubles" && size === 8 ? 4 : size;
    return {
      tournament,
      eventFormat: format,
      podiumSize: normalizedSize,
      top8Layout,
      includeSeeds: typeof saved.includeSeeds === "boolean" ? saved.includeSeeds : defaults.includeSeeds,
      entrants: createEntrants(entrantStorageCount(format), format, savedEntrants as EntrantFormState[]),
      bracketUrl: stringValue(saved.bracketUrl),
    };
  } catch {
    return defaults;
  }
}

function loadPreferredFont(): PodiumFont {
  try {
    const saved = window.localStorage.getItem(PREFERRED_FONT_KEY);
    return isPodiumFont(saved) ? saved : "tyrowo";
  } catch {
    return "tyrowo";
  }
}

function entrantStorageCount(format: EventFormat): number {
  return format === "singles" ? 8 : 4;
}
function recommendedPodiumSize(format: EventFormat, entrantsCount?: number): PodiumSize {
  if (entrantsCount !== undefined && entrantsCount <= 9) return 3;
  if (format === "singles" && entrantsCount !== undefined && entrantsCount <= 14) return 4;
  return format === "singles" ? 8 : 4;
}

function importFormat(value: unknown): EventFormat | undefined {
  if (typeof value !== "string") return undefined;
  const format = value.toLowerCase();
  if (format.includes("double")) return "doubles";
  if (format.includes("single")) return "singles";
  return undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(...values: unknown[]): string {
  const match = values.find(
    (value) => typeof value === "string" || typeof value === "number",
  );
  return match === undefined ? "" : String(match);
}

function splitTournamentName(name: string): { title: string; subtitle: string } {
  const [title, ...subtitleParts] = name.split(":");
  return {
    title: title.trim() || name.trim(),
    subtitle: subtitleParts.join(":").trim(),
  };
}

function firstCharacter(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) return {};
  if (isRecord(value.character)) return value.character;
  if (Array.isArray(value.characters) && isRecord(value.characters[0])) {
    return value.characters[0];
  }
  return {};
}

function importedCharacters(value: unknown): Record<string, unknown>[] {
  if (!isRecord(value) || !Array.isArray(value.characters)) return [];
  return value.characters.filter(isRecord);
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function ordinalPlace(index: number): string {
  const num = placementForIndex(index, 8);
  if (num === 1) return "1st Place";
  if (num === 2) return "2nd Place";
  if (num === 3) return "3rd Place";
  return `${num}th Place`;
}

function placementForIndex(index: number, podiumSize: PodiumSize): number {
  if (podiumSize === 8 && index >= 4) return index < 6 ? 5 : 7;
  return index + 1;
}

function App() {
  const [health, setHealth] = useState<"checking" | "online" | "offline">(
    "checking",
  );
  const [renderCount, setRenderCount] = useState<number | null>(null);
  const [fighters, setFighters] = useState<FighterOption[]>(DEFAULT_FIGHTERS);
  const [optionsError, setOptionsError] = useState("");
  const [initialSelections] = useState(loadPodiumSelections);
  const [tournament, setTournament] = useState<TournamentForm>(initialSelections.tournament);
  const [eventFormat, setEventFormat] = useState<EventFormat>(initialSelections.eventFormat);
  const [podiumSize, setPodiumSize] = useState<PodiumSize>(initialSelections.podiumSize);
  const [top8Layout, setTop8Layout] = useState<Top8Layout>(initialSelections.top8Layout);
  const [podiumFont, setPodiumFont] = useState<PodiumFont>(loadPreferredFont);
  const [includeSeeds, setIncludeSeeds] = useState(initialSelections.includeSeeds);
  const [entrants, setEntrants] = useState<EntrantFormState[]>(initialSelections.entrants);
  const [bracketUrl, setBracketUrl] = useState(initialSelections.bracketUrl);
  const [importState, setImportState] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [renderError, setRenderError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [favorites, setFavorites] = useState<FavoritesData>(() => loadFavorites());
  const skipNextSelectionSave = useRef(false);

  useEffect(() => {
    let active = true;

    getHealth()
      .then((result) => {
        if (active) {
          setHealth(
            result.status?.toLowerCase() === "error" ? "offline" : "online",
          );
        }
      })
      .catch(() => {
        if (active) setHealth("offline");
      });

    getStats()
      .then((result) => {
        if (active && Number.isInteger(result.render_count) && result.render_count >= 0) {
          setRenderCount(result.render_count);
        }
      })
      .catch(() => {});

    getOptions()
      .then((result) => {
        if (!active) return;
        const roster = DEFAULT_FIGHTERS.map((fighter) => result.fighters.find((item) => item.name === fighter.name) ?? fighter);
        setFighters(roster);
        setOptionsError("");
        const first = roster[0];
        const firstOption = first?.options[0];
        if (first) {
          setEntrants((current) =>
            current.map((entrant) => {
              if (entrant.kind === "singles") {
                const character = entrant.characters[0] ?? createCharacterForm();
                if (character.fighter) return entrant;
                return {
                  ...entrant,
                  characters: [
                    {
                      fighter: first.name,
                      color: firstOption?.color ?? "",
                      pose: "",
                      mirrorHorizontally: false,
                    },
                  ],
                };
              }

              const firstMember = entrant.entrant_1.characters[0] ?? createCharacterForm();
              const secondMember = entrant.entrant_2.characters[0] ?? createCharacterForm();
              return {
                ...entrant,
                entrant_1: {
                  ...entrant.entrant_1,
                  characters: [
                    {
                      fighter: firstMember.fighter || first.name,
                      color: firstMember.color || (firstOption?.color ?? ""),
                      pose: firstMember.pose,
                      mirrorHorizontally: firstMember.mirrorHorizontally === true,
                    },
                  ],
                },
                entrant_2: {
                  ...entrant.entrant_2,
                  characters: [
                    {
                      fighter: secondMember.fighter || first.name,
                      color: secondMember.color || (firstOption?.color ?? ""),
                      pose: secondMember.pose,
                      mirrorHorizontally: secondMember.mirrorHorizontally === true,
                    },
                  ],
                },
              };
            }),
          );
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setOptionsError(
            error instanceof Error ? error.message : "Could not load fighters.",
          );
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl],
  );

  useEffect(() => {
    if (skipNextSelectionSave.current) {
      skipNextSelectionSave.current = false;
      return;
    }
    try {
      window.localStorage.setItem(PODIUM_SELECTIONS_KEY, JSON.stringify({
        tournament,
        eventFormat,
        podiumSize,
        top8Layout,
        includeSeeds,
        entrants,
        bracketUrl,
      } satisfies PodiumSelections));
    } catch {
      // Keep the maker usable if browser storage is unavailable.
    }
  }, [bracketUrl, entrants, eventFormat, includeSeeds, podiumSize, top8Layout, tournament]);

  useEffect(() => {
    try {
      window.localStorage.setItem(PREFERRED_FONT_KEY, podiumFont);
    } catch {
      // Keep the maker usable if browser storage is unavailable.
    }
  }, [podiumFont]);
  const payload = useMemo(
    () => ({
      mode: eventFormat === "singles" && podiumSize === 8 && top8Layout === "four_podium"
        ? "singles_top_8_four_podium"
        : `${eventFormat}_top_${podiumSize}`,
      font: podiumFont,
      tournament: {
        title: tournament.title.trim(),
        date: tournament.date,
        entrants_count: Number(tournament.entrantsCount),
        subtitle: tournament.subtitle.trim() || null,
        event: tournament.event.trim() || null,
        link: tournament.link.trim() || null,
        event_format: eventFormat,
      },
      entrants: entrants.slice(0, podiumSize).map((entrant, index) => {
        if (entrant.kind === "singles") {
          return {
            tag: entrant.tag.trim(),
            seed: includeSeeds && entrant.seed ? Number(entrant.seed) : null,
            placement: placementForIndex(index, podiumSize),
            characters: entrant.characters.map((character) => ({
              melee_fighter_name: character.fighter,
              color: character.color || null,
              pose: character.pose || null,
              mirror_horizontally: character.mirrorHorizontally,
            })),
          };
        }

        return {
          team_name: entrant.team_name.trim(),
          seed: includeSeeds && entrant.seed ? Number(entrant.seed) : null,
          placement: placementForIndex(index, podiumSize),
          team_color: entrant.team_color.trim() || null,
          entrant_1: {
            tag: entrant.entrant_1.tag.trim(),
            characters: entrant.entrant_1.characters.map((character) => ({
              melee_fighter_name: character.fighter,
              color: character.color || null,
              pose: character.pose || null,
              mirror_horizontally: character.mirrorHorizontally,
            })),
          },
          entrant_2: {
            tag: entrant.entrant_2.tag.trim(),
            characters: entrant.entrant_2.characters.map((character) => ({
              melee_fighter_name: character.fighter,
              color: character.color || null,
              pose: character.pose || null,
              mirror_horizontally: character.mirrorHorizontally,
            })),
          },
        };
      }),
    }),
    [entrants, eventFormat, includeSeeds, podiumFont, podiumSize, top8Layout, tournament],
  );

  function startFresh() {
    const defaults = defaultPodiumSelections();
    skipNextSelectionSave.current = true;
    try {
      window.localStorage.removeItem(PODIUM_SELECTIONS_KEY);
    } catch {
      // State is still reset for the current session when storage is unavailable.
    }
    setTournament(defaults.tournament);
    setEventFormat(defaults.eventFormat);
    setPodiumSize(defaults.podiumSize);
    setTop8Layout(defaults.top8Layout);
    setIncludeSeeds(defaults.includeSeeds);
    setEntrants(defaults.entrants);
    setBracketUrl(defaults.bracketUrl);
    setImportState("");
    setRenderError("");
    setCopyStatus("");
  }
  function selectFormat(format: EventFormat) {
    const size = recommendedPodiumSize(format);
    setEventFormat(format);
    setPodiumSize(size);
    setEntrants((current) => createEntrants(entrantStorageCount(format), format, current));
  }

  function selectPodiumSize(size: PodiumSize, layout?: Top8Layout) {
    setPodiumSize(size);
    if (layout) setTop8Layout(layout);
    setEntrants((current) => createEntrants(entrantStorageCount(eventFormat), eventFormat, current));
  }

  function fighterByName(name: string): FighterOption | undefined {
    return fighters.find((fighter) => fighter.name === name);
  }

  function updateSinglesEntrant(
    index: number,
    field: "tag" | "seed",
    value: string,
  ) {
    setEntrants((current) =>
      current.map((entrant, entrantIndex) => {
        if (entrantIndex !== index || entrant.kind !== "singles") return entrant;
        return { ...entrant, [field]: value };
      }),
    );
  }

  function updateDoublesTeam(
    index: number,
    field: "team_name" | "seed" | "team_color",
    value: string,
  ) {
    setEntrants((current) =>
      current.map((entrant, entrantIndex) => {
        if (entrantIndex !== index || entrant.kind !== "doubles") return entrant;
        return { ...entrant, [field]: value };
      }),
    );
  }

  function updateEntrantTag(index: number, side: "entrant_1" | "entrant_2", value: string) {
    setEntrants((current) =>
      current.map((entrant, entrantIndex) => {
        if (entrantIndex !== index || entrant.kind !== "doubles") return entrant;
        return side === "entrant_1"
          ? { ...entrant, entrant_1: { ...entrant.entrant_1, tag: value } }
          : { ...entrant, entrant_2: { ...entrant.entrant_2, tag: value } };
      }),
    );
  }

  function setEntrantCharacters(index: number, side: "singles" | "entrant_1" | "entrant_2", characters: CharacterForm[]) {
    setEntrants((current) => current.map((entrant, entrantIndex) => {
      if (entrantIndex !== index) return entrant;
      if (entrant.kind === "singles") return { ...entrant, characters };
      return side === "entrant_1" ? { ...entrant, entrant_1: { ...entrant.entrant_1, characters } } : { ...entrant, entrant_2: { ...entrant.entrant_2, characters } };
    }));
  }
  function updateCharacter(index: number, side: "singles" | "entrant_1" | "entrant_2", characterIndex: number, field: "fighter" | "color" | "pose", value: string) {
    setEntrants((current) => current.map((entrant, entrantIndex) => {
      if (entrantIndex !== index) return entrant;
      const updateCharacters = (characters: CharacterForm[]) => characters.map((character, currentIndex) => {
        if (currentIndex !== characterIndex) return character;
        if (field === "fighter") {
          if (characters.some((character, currentIndex) => currentIndex !== characterIndex && character.fighter === value)) return character;
          const option = fighterByName(value)?.options[0];
          return { fighter: value, color: option?.color ?? "", pose: "", mirrorHorizontally: character.mirrorHorizontally === true };
        }
        if (field === "color") {
          return { ...character, color: value, pose: "" };
        }
        return { ...character, pose: value };
      });
      if (entrant.kind === "singles") return { ...entrant, characters: updateCharacters(entrant.characters) };
      const member = side === "entrant_1" ? entrant.entrant_1 : entrant.entrant_2;
      const nextMember = { ...member, characters: updateCharacters(member.characters) };
      return side === "entrant_1" ? { ...entrant, entrant_1: nextMember } : { ...entrant, entrant_2: nextMember };
    }));
  }

  function addCharacter(index: number, side: "singles" | "entrant_1" | "entrant_2") {
    setEntrants((current) => current.map((entrant, entrantIndex) => {
      if (entrantIndex !== index) return entrant;
      if (entrant.kind === "singles") return entrant.characters.length >= MELEE_FIGHTER_NAMES.length ? entrant : { ...entrant, characters: [...entrant.characters, createCharacterForm()] };
      const member = side === "entrant_1" ? entrant.entrant_1 : entrant.entrant_2;
      const nextMember = member.characters.length >= MELEE_FIGHTER_NAMES.length ? member : { ...member, characters: [...member.characters, createCharacterForm()] };
      return side === "entrant_1" ? { ...entrant, entrant_1: nextMember } : { ...entrant, entrant_2: nextMember };
    }));
  }

  function removeCharacter(index: number, side: "singles" | "entrant_1" | "entrant_2", characterIndex: number) {
    setEntrants((current) => current.map((entrant, entrantIndex) => {
      if (entrantIndex !== index) return entrant;
      if (entrant.kind === "singles") return { ...entrant, characters: entrant.characters.filter((_, currentIndex) => currentIndex !== characterIndex) };
      const member = side === "entrant_1" ? entrant.entrant_1 : entrant.entrant_2;
      const nextMember = { ...member, characters: member.characters.filter((_, currentIndex) => currentIndex !== characterIndex) };
      return side === "entrant_1" ? { ...entrant, entrant_1: nextMember } : { ...entrant, entrant_2: nextMember };
    }));
  }
  function changeFavorites(next: FavoritesData) {
    setFavorites(saveFavorites(next));
  }

  function applyFavoriteSingles(index: number, favorite: FavoriteSinglesEntrant) {
    setEntrants((current) => current.map((entrant, currentIndex) => currentIndex === index && entrant.kind === "singles" ? { ...entrant, tag: favorite.tag, characters: favorite.characters.map((character) => ({ ...character })) } : entrant));
  }

  function applyFavoriteMember(index: number, side: "entrant_1" | "entrant_2", favorite: FavoriteSinglesEntrant) {
    setEntrants((current) => current.map((entrant, currentIndex) => {
      if (currentIndex !== index || entrant.kind !== "doubles") return entrant;
      const member = { tag: favorite.tag, characters: favorite.characters.map((character) => ({ ...character })) };
      return side === "entrant_1" ? { ...entrant, entrant_1: member } : { ...entrant, entrant_2: member };
    }));
  }

  function applyFavoriteTeam(index: number, favorite: FavoriteDoublesTeam) {
    setEntrants((current) => current.map((entrant, currentIndex) => currentIndex === index && entrant.kind === "doubles" ? { ...entrant, team_name: favorite.team_name, team_color: favorite.team_color, entrant_1: { tag: favorite.entrant_1.tag, characters: favorite.entrant_1.characters.map((character) => ({ ...character })) }, entrant_2: { tag: favorite.entrant_2.tag, characters: favorite.entrant_2.characters.map((character) => ({ ...character })) } } : entrant));
  }

  function toggleSinglesFavorite(entrant: SinglesEntrantForm, checked: boolean) {
    const current = favorites.singles.find((favorite) => favorite.tag === entrant.tag);
    if (!checked) return changeFavorites({ ...favorites, singles: favorites.singles.filter((favorite) => favorite.tag !== entrant.tag) });
    const next = { id: current?.id ?? newFavoriteId(), tag: entrant.tag, characters: entrant.characters.map((character) => ({ ...character })), primary: current?.primary ?? false };
    changeFavorites({ ...favorites, singles: current ? favorites.singles.map((favorite) => favorite.id === current.id ? next : favorite) : [...favorites.singles, next] });
  }

  function toggleDoublesFavorite(team: DoublesTeamForm, checked: boolean) {
    const current = favorites.doubles.find((favorite) => favorite.team_name === team.team_name);
    if (!checked) return changeFavorites({ ...favorites, doubles: favorites.doubles.filter((favorite) => favorite.team_name !== team.team_name) });
    const next = { id: current?.id ?? newFavoriteId(), team_name: team.team_name, team_color: team.team_color, entrant_1: { tag: team.entrant_1.tag, characters: team.entrant_1.characters.map((character) => ({ ...character })) }, entrant_2: { tag: team.entrant_2.tag, characters: team.entrant_2.characters.map((character) => ({ ...character })) } };
    changeFavorites({ ...favorites, doubles: current ? favorites.doubles.map((favorite) => favorite.id === current.id ? next : favorite) : [...favorites.doubles, next] });
  }
  function applyImport(result: unknown) {
    if (!isRecord(result)) {
      throw new Error("The bracket response was not in the expected format.");
    }

    const importedTournament = isRecord(result.tournament)
      ? result.tournament
      : result;
    const entrantsCount = Number(
      stringValue(
        importedTournament.entrants_count,
        importedTournament.entrant_count,
        result.entrants_count,
      ),
    );
    const importedFormat = importFormat(
      importedTournament.event_format ??
        importedTournament.format ??
        result.event_format ??
        result.format,
    );
    const nextFormat = importedFormat ?? eventFormat;
    const nextSize = recommendedPodiumSize(
      nextFormat,
      Number.isFinite(entrantsCount) && entrantsCount > 0 ? entrantsCount : undefined,
    );

    const importedName = stringValue(
      importedTournament.title,
      importedTournament.name,
      result.title,
    );
    const { title: importedTitle, subtitle: titleSubtitle } =
      splitTournamentName(importedName);

    setEventFormat(nextFormat);
    setPodiumSize(nextSize);
    setTournament((current) => ({
      title: importedTitle || current.title,
      date:
        stringValue(importedTournament.date, result.date).slice(0, 10) ||
        current.date,
      entrantsCount:
        stringValue(
          importedTournament.entrants_count,
          importedTournament.entrant_count,
          result.entrants_count,
        ) || current.entrantsCount,
      subtitle: titleSubtitle || stringValue(importedTournament.subtitle, result.subtitle) || current.subtitle,
      event: stringValue(importedTournament.event, result.event) || current.event,
      link: stringValue(importedTournament.link, result.link) || current.link,
    }));

    const importedEntrants = Array.isArray(result.entrants)
      ? result.entrants.slice(0, entrantStorageCount(nextFormat))
      : [];
    const hasImportedSeeds = importedEntrants.some((entrant) => {
      if (!isRecord(entrant)) return false;
      const seed = Number(entrant.seed);
      return Number.isInteger(seed) && seed > 0;
    });
    setIncludeSeeds(hasImportedSeeds);
    setEntrants((current) =>
      createEntrants(entrantStorageCount(nextFormat), nextFormat, current).map((existing, index) => {
        const imported = importedEntrants[index];
        if (!isRecord(imported)) return existing;

        const importedCharacterForms = importedCharacters(imported).map((character) => createCharacterForm(stringValue(character.fighter, character.melee_fighter_name), stringValue(character.color), stringValue(character.pose)));
        const character = firstCharacter(imported);
        const importedCharacter = importedCharacterForms[0] ?? createCharacterForm(stringValue(imported.fighter, imported.melee_fighter_name, character.fighter, character.melee_fighter_name), stringValue(imported.color, character.color), stringValue(imported.pose, character.pose));

        if (nextFormat === "singles") {
          const importedTag = stringValue(
            imported.tag,
            imported.name,
            imported.player_tag,
          );
          const matchingFavorite = favoriteForImport(favorites.singles, importedTag, importedCharacterForms);
          return createSinglesEntrant(index + 1, {
            kind: "singles",
            tag: matchingFavorite?.tag || importedTag || (existing.kind === "singles" ? existing.tag : ""),
            seed: stringValue(imported.seed),
            characters:
              matchingFavorite
                ? matchingFavorite.characters.map((favoriteCharacter) => ({
                    ...favoriteCharacter,
                  }))
                : importedCharacterForms.length ? importedCharacterForms : [importedCharacter],
          });
        }
        const entrantOne = isRecord(imported.entrant_1)
          ? imported.entrant_1
          : isRecord(imported.player_1)
            ? imported.player_1
            : imported;
        const entrantTwo = isRecord(imported.entrant_2)
          ? imported.entrant_2
          : isRecord(imported.player_2)
            ? imported.player_2
            : imported;
        const entrantOneCharacter = firstCharacter(entrantOne);
        const entrantTwoCharacter = firstCharacter(entrantTwo);

        return createDoublesTeam(index + 1, {
          kind: "doubles",
          team_name:
            stringValue(imported.team_name, imported.tag, imported.name) ||
            (existing.kind === "doubles" ? existing.team_name : ""),
          seed: stringValue(imported.seed),
          team_color:
            stringValue(imported.team_color, imported.color) ||
            (existing.kind === "doubles" ? existing.team_color : ""),
          entrant_1: {
            tag:
              stringValue(
                entrantOne.tag,
                entrantOne.name,
                entrantOne.player_tag,
              ) ||
              (existing.kind === "doubles" ? existing.entrant_1.tag : ""),
            characters: [
              createCharacterForm(
                stringValue(
                  entrantOne.fighter,
                  entrantOne.melee_fighter_name,
                  entrantOneCharacter.fighter,
                  entrantOneCharacter.melee_fighter_name,
                ),
                stringValue(entrantOne.color, entrantOneCharacter.color),
                stringValue(entrantOne.pose, entrantOneCharacter.pose),
              ),
            ],
          },
          entrant_2: {
            tag:
              stringValue(
                entrantTwo.tag,
                entrantTwo.name,
                entrantTwo.player_tag,
              ) ||
              (existing.kind === "doubles" ? existing.entrant_2.tag : ""),
            characters: [
              createCharacterForm(
                stringValue(
                  entrantTwo.fighter,
                  entrantTwo.melee_fighter_name,
                  entrantTwoCharacter.fighter,
                  entrantTwoCharacter.melee_fighter_name,
                ),
                stringValue(entrantTwo.color, entrantTwoCharacter.color),
                stringValue(entrantTwo.pose, entrantTwoCharacter.pose),
              ),
            ],
          },
        });
      }),
    );
  }

  async function handleImport(event: FormEvent) {
    event.preventDefault();
    setIsImporting(true);
    setImportState("");

    try {
      const result = await importBracket(bracketUrl.trim(), 8);
      applyImport(result);
      setImportState("Bracket imported. Review the fields before rendering.");
    } catch (error) {
      setImportState(
        error instanceof Error ? error.message : "Bracket import failed.",
      );
    } finally {
      setIsImporting(false);
    }
  }

  async function handleRender(event: FormEvent) {
    event.preventDefault();
    setIsRendering(true);
    setRenderError("");

    try {
      const image = await renderPodium(payload);
      const nextUrl = URL.createObjectURL(image);
      setPreviewUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return nextUrl;
      });
    } catch (error) {
      setRenderError(
        error instanceof Error ? error.message : "Could not render the podium.",
      );
    } finally {
      setIsRendering(false);
    }
  }

  async function copyPayload() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setCopyStatus("Copied JSON.");
    } catch {
      setCopyStatus("Could not copy JSON.");
    }
  }

  function handleDownload() {
    void recordDownload()
      .then((result) => setRenderCount(result.render_count))
      .catch(() => {});
  }

  const downloadName = `${tournament.title || "melee"}-podium`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  if (window.location.pathname.replace(/\/+$/, "").endsWith("favorites_management")) {
    return <FavoritesManagement favorites={favorites} fighters={fighters} renderCount={renderCount} onChange={changeFavorites} onBack={() => { window.location.href = import.meta.env.BASE_URL; }} />;
  }

  return (
    <main className="page-shell">
      <header className="site-header">
        <div>
          <h1>Melee Podium Maker</h1>
          <p className="lede">
            Enter your bracket information and then render a
            downloadable podium graphic. 
            <br/>Expedite the process by importing a bracket link from start.gg or challonge. 
            <br/>Save entrants (via localstorage) to reuse in later podiums to save time picking characters and colors.
          </p>
        </div>
        <a className="button-link" href={`${import.meta.env.BASE_URL}favorites_management`}>Manage favorites</a>
        <div className={`health health--${health}`} role="status">
          <span aria-hidden="true" />
          API {health}
        </div>
      </header>

      <div className="start-fresh-actions">
        <button className="button-danger" type="button" onClick={startFresh}>
          Start Fresh - Clear Prior Selections
        </button>
      </div>

      <section className="panel">
        <h2>Import a bracket</h2>
        <form className="import-form" onSubmit={handleImport}>
          <label>
            Public bracket URL
            <input
              type="url"
              value={bracketUrl}
              onChange={(event) => setBracketUrl(event.target.value)}
              placeholder="https://www.start.gg/tournament/..."
              required
            />
          </label>
          <button type="submit" disabled={isImporting}>
            {isImporting ? "Importing..." : "Import"}
          </button>
        </form>
        {importState && <p className="form-message">{importState}</p>}
      </section>

      <form onSubmit={handleRender}>
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Podium Format Settings</h2>
              <p>Choose the event type, layout, typeface, and displayed details.</p>
            </div>
          </div>
          <div className="format-controls">
            <fieldset className="choice-group">
              <legend>Format</legend>
              {(["singles", "doubles"] as const).map((format) => (
                <label className="choice" key={format}>
                  <input type="radio" name="event-format" checked={eventFormat === format} onChange={() => selectFormat(format)} />
                  {format[0].toUpperCase() + format.slice(1)}
                </label>
              ))}
            </fieldset>
            <fieldset className="choice-group">
              <legend>Podium size</legend>
              {([
                { size: 3 as const, label: "Top 3" },
                { size: 4 as const, label: "Top 4" },
                ...(eventFormat === "singles"
                  ? [
                      { size: 8 as const, layout: "all_showing" as const, label: "Top 8 (All Showing)" },
                      { size: 8 as const, layout: "four_podium" as const, label: "Top 8 (4 Podium)" },
                    ]
                  : []),
              ]).map((option) => (
                <label className="choice" key={`${option.size}-${option.layout ?? "standard"}`}>
                  <input
                    type="radio"
                    name="podium-size"
                    checked={
                      podiumSize === option.size
                      && (option.size !== 8 || top8Layout === option.layout)
                    }
                    onChange={() => selectPodiumSize(option.size, option.layout)}
                  />
                  {option.label}
                </label>
              ))}
            </fieldset>
            <label>
              Font
              <select value={podiumFont} onChange={(event) => setPodiumFont(event.target.value as PodiumFont)}>
                {PODIUM_FONTS.map((font) => <option key={font.value} value={font.value}>{font.label}</option>)}
              </select>
            </label>
            <label className="choice">
              <input type="checkbox" checked={includeSeeds} onChange={(event) => setIncludeSeeds(event.target.checked)} />
              Include seeds
            </label>
          </div>
        </section>

        <section className="panel">
          <h2>Tournament Info</h2>
          <div className="field-grid">
            <label className="field-grid__wide">
              Title
              <input
                value={tournament.title}
                onChange={(event) =>
                  setTournament((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
                placeholder="Friday Night Melee"
                required
              />
            </label>
            <label>
              Date
              <input
                type="date"
                value={tournament.date}
                onChange={(event) =>
                  setTournament((current) => ({
                    ...current,
                    date: event.target.value,
                  }))
                }
                required
              />
            </label>
            <label>
              Entrant count
              <input
                type="number"
                min="1"
                value={tournament.entrantsCount}
                onChange={(event) =>
                  setTournament((current) => ({
                    ...current,
                    entrantsCount: event.target.value,
                  }))
                }
                required
              />
            </label>
            <label className="field-grid__wide">
              Subtitle (optional)
              <input
                value={tournament.subtitle}
                onChange={(event) => setTournament((current) => ({ ...current, subtitle: event.target.value }))}
                placeholder="Weekly #42"
              />
            </label>
            <label>
              Event (optional)
              <input
                value={tournament.event}
                onChange={(event) => setTournament((current) => ({ ...current, event: event.target.value }))}
                placeholder={`Melee ${eventFormat === "doubles" ? "Doubles" : "Singles"}`}
              />
            </label>
            <label>
              Tournament link (optional)
              <input
                type="url"
                value={tournament.link}
                onChange={(event) => setTournament((current) => ({ ...current, link: event.target.value }))}
                placeholder="https://start.gg/..."
              />
            </label>
          </div>
        </section>

        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Top {podiumSize} Entrants</h2>
              <p>Character colors and poses come from the renderer.</p>
            </div>
            {optionsError && (
              <p className="error" role="alert">
                {optionsError}
              </p>
            )}
          </div>

          <div className="entrant-grid">
            {entrants.slice(0, podiumSize).map((entrant, index) => {
              if (entrant.kind === "singles") {
                const character = entrant.characters[0] ?? createCharacterForm();
                const fighter = fighterByName(character.fighter);
                const colors = unique(
                  (fighter?.options ?? []).map((option) => option.color),
                );
                const poses = unique(
                  (fighter?.options ?? [])
                    .filter((option) => option.color === character.color)
                    .map((option) => option.pose),
                );

                return (
                  <fieldset className="entrant-card" key={index}>
                    <legend>{ordinalPlace(index)}</legend>
                    <SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applyFavoriteSingles(index, favorite)} />
{includeSeeds && (
                      <label>
                        Seed
                        <input type="number" min="1" value={entrant.seed} onChange={(event) => updateSinglesEntrant(index, "seed", event.target.value)} />
                      </label>
                    )}
                    <EntrantCharacterEditor tag={entrant.tag} tagPlaceholder={`Player ${index + 1}`} characters={entrant.characters} fighters={fighters} onTagChange={(tag) => updateSinglesEntrant(index, "tag", tag)} onChange={(characters) => setEntrantCharacters(index, "singles", characters)} />
                    <label className="choice"><input type="checkbox" checked={favorites.singles.some((favorite) => favorite.tag === entrant.tag)} onChange={(event) => toggleSinglesFavorite(entrant, event.target.checked)} /> Save or update favorite entrant</label>
                  </fieldset>
                );
              }

              const teamCharacterOne = entrant.entrant_1.characters[0] ?? createCharacterForm();
              const teamCharacterTwo = entrant.entrant_2.characters[0] ?? createCharacterForm();
              const fighterOne = fighterByName(teamCharacterOne.fighter);
              const fighterTwo = fighterByName(teamCharacterTwo.fighter);
              const colorsOne = unique(
                (fighterOne?.options ?? []).map((option) => option.color),
              );
              const colorsTwo = unique(
                (fighterTwo?.options ?? []).map((option) => option.color),
              );
              const posesOne = unique(
                (fighterOne?.options ?? [])
                  .filter((option) => option.color === teamCharacterOne.color)
                  .map((option) => option.pose),
              );
              const posesTwo = unique(
                (fighterTwo?.options ?? [])
                  .filter((option) => option.color === teamCharacterTwo.color)
                  .map((option) => option.pose),
              );

              return (
                <fieldset className="entrant-card" key={index}>
                  <legend>{ordinalPlace(index)}</legend>
                  <DoublesFavoritePicker favorites={favorites.doubles} onChoose={(favorite) => applyFavoriteTeam(index, favorite)} />
                  <label>
                    Team name
                    <input
                      value={entrant.team_name}
                      onChange={(event) =>
                        updateDoublesTeam(index, "team_name", event.target.value)
                      }
                      placeholder={`Team ${index + 1}`}
                      required
                    />
                  </label>
                  {includeSeeds && (
                    <label>
                      Seed
                      <input type="number" min="1" value={entrant.seed} onChange={(event) => updateDoublesTeam(index, "seed", event.target.value)} />
                    </label>
                  )}
                  <label>
                    Team color
                    <select
                      value={entrant.team_color || "random"}
                      onChange={(event) =>
                        updateDoublesTeam(index, "team_color", event.target.value)
                      }
                    >
                      <option value="random">Random</option>
                      <option value="red">Red</option>
                      <option value="green">Green</option>
                      <option value="blue">Blue</option>
                    </select>
                  </label>
<div className="row-fields">
                    <fieldset className="entrant-card" style={{ padding: "0.75rem" }}>
                      <legend>Entrant 1</legend>
                      <SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applyFavoriteMember(index, "entrant_1", favorite)} />
                      <EntrantCharacterEditor tag={entrant.entrant_1.tag} tagLabel="Entrant 1 tag" tagPlaceholder={`Player 1 ${index + 1}`} characters={entrant.entrant_1.characters} fighters={fighters} onTagChange={(tag) => updateEntrantTag(index, "entrant_1", tag)} onChange={(characters) => setEntrantCharacters(index, "entrant_1", characters)} />
                    </fieldset>

                    <fieldset className="entrant-card" style={{ padding: "0.75rem" }}>
                      <legend>Entrant 2</legend>
                      <SinglesFavoritePicker favorites={favorites.singles} onChoose={(favorite) => applyFavoriteMember(index, "entrant_2", favorite)} />
                      <EntrantCharacterEditor tag={entrant.entrant_2.tag} tagLabel="Entrant 2 tag" tagPlaceholder={`Player 2 ${index + 1}`} characters={entrant.entrant_2.characters} fighters={fighters} onTagChange={(tag) => updateEntrantTag(index, "entrant_2", tag)} onChange={(characters) => setEntrantCharacters(index, "entrant_2", characters)} />
                    </fieldset>
                  </div>
                  <label className="choice"><input type="checkbox" checked={favorites.doubles.some((favorite) => favorite.team_name === entrant.team_name)} onChange={(event) => toggleDoublesFavorite(entrant, event.target.checked)} /> Save or update favorite doubles team</label>
                </fieldset>
              );
            })}
          </div>

          <details className="payload-preview">
            <summary>Preview API request</summary>
            <div className="payload-preview__actions">
              <button type="button" onClick={copyPayload}>Copy JSON</button>
              {copyStatus && <span role="status">{copyStatus}</span>}
            </div>
            <pre>{JSON.stringify(payload, null, 2)}</pre>
          </details>

          <div className="form-actions">
            <button className="button-primary" type="submit" disabled={isRendering}>
              {isRendering ? "Rendering..." : "Render podium"}
            </button>
            {renderError && (
              <p className="error" role="alert">
                {renderError}
              </p>
            )}
          </div>
        </section>
      </form>

      <section className="panel preview-panel">
        <div className="section-heading">
          <div>
            <h2>Preview</h2>
            <p>Your latest render will appear here.</p>
          </div>
          {previewUrl && (
            <a
              className="button-link"
              href={previewUrl}
              download={`${downloadName || "melee-podium"}.png`}
              onClick={handleDownload}
            >
              Download High Resolution Image
            </a>
          )}
        </div>
        <div className="preview-frame">
          {previewUrl ? (
            <img src={previewUrl} alt="Rendered tournament podium" />
          ) : (
            <p>Complete the form and select "Render podium."</p>
          )}
        </div>
      </section>
      <Footer renderCount={renderCount} />
    </main>
  );
}

export default App;


