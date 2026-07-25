import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  FighterOption,
  getHealth,
  getOptions,
  importBracket,
  renderPodium,
} from "./api";

interface CharacterForm {
  fighter: string;
  color: string;
  pose: string;
}

interface EntrantForm {
  tag: string;
  characters: CharacterForm[];
}

interface SinglesEntrantForm {
  kind: "singles";
  tag: string;
  seed: string;
  placement: string;
  characters: CharacterForm[];
}

interface DoublesTeamForm {
  kind: "doubles";
  team_name: string;
  seed: string;
  placement: string;
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

type EventFormat = "singles" | "doubles";
type PodiumSize = 3 | 4 | 8;

function createCharacterForm(
  fighter = "",
  color = "",
  pose = "",
): CharacterForm {
  return { fighter, color, pose };
}

function createEntrantForm(existing?: EntrantForm): EntrantForm {
  return {
    tag: existing?.tag ?? "",
    characters: existing?.characters?.length
      ? existing.characters.map((character) => ({ ...character }))
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
    placement: existing?.placement ?? String(placement),
    characters: existing?.characters?.length
      ? existing.characters.map((character) => ({ ...character }))
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
    placement: existing?.kind === "doubles" ? existing.placement : String(placement),
    team_color: existing?.kind === "doubles" ? existing.team_color : "",
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
          placement: existingEntry.placement,
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

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function App() {
  const [health, setHealth] = useState<"checking" | "online" | "offline">(
    "checking",
  );
  const [fighters, setFighters] = useState<FighterOption[]>([]);
  const [optionsError, setOptionsError] = useState("");
  const [tournament, setTournament] = useState<TournamentForm>({
    title: "",
    date: new Date().toISOString().slice(0, 10),
    entrantsCount: "16",
    subtitle: "",
    event: "",
    link: "",
  });
  const [eventFormat, setEventFormat] = useState<EventFormat>("singles");
  const [podiumSize, setPodiumSize] = useState<PodiumSize>(8);
  const [entrants, setEntrants] = useState<EntrantFormState[]>(() =>
    createEntrants(8, "singles"),
  );
  const [bracketUrl, setBracketUrl] = useState("");
  const [importState, setImportState] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [renderError, setRenderError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");

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

    getOptions()
      .then((result) => {
        if (!active) return;
        setFighters(result.fighters);
        setOptionsError("");
        const first = result.fighters[0];
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
                      pose: firstOption?.pose ?? "",
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
                      pose: firstMember.pose || (firstOption?.pose ?? ""),
                    },
                  ],
                },
                entrant_2: {
                  ...entrant.entrant_2,
                  characters: [
                    {
                      fighter: secondMember.fighter || first.name,
                      color: secondMember.color || (firstOption?.color ?? ""),
                      pose: secondMember.pose || (firstOption?.pose ?? ""),
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

  const payload = useMemo(
    () => ({
      mode: `${eventFormat}_top_${podiumSize}`,
      tournament: {
        title: tournament.title.trim(),
        date: tournament.date,
        entrants_count: Number(tournament.entrantsCount),
        subtitle: tournament.subtitle.trim() || null,
        event: tournament.event.trim() || null,
        link: tournament.link.trim() || null,
        event_format: eventFormat,
      },
      entrants: entrants.map((entrant) => {
        if (entrant.kind === "singles") {
          const character = entrant.characters[0] ?? createCharacterForm();
          return {
            tag: entrant.tag.trim(),
            seed: entrant.seed ? Number(entrant.seed) : null,
            placement: Number(entrant.placement),
            characters: [
              {
                melee_fighter_name: character.fighter,
                color: character.color,
                pose: character.pose,
              },
            ],
          };
        }

        const entrantOneCharacter =
          entrant.entrant_1.characters[0] ?? createCharacterForm();
        const entrantTwoCharacter =
          entrant.entrant_2.characters[0] ?? createCharacterForm();

        return {
          team_name: entrant.team_name.trim(),
          seed: entrant.seed ? Number(entrant.seed) : null,
          placement: Number(entrant.placement),
          team_color: entrant.team_color.trim() || null,
          entrant_1: {
            tag: entrant.entrant_1.tag.trim(),
            characters: [
              {
                melee_fighter_name: entrantOneCharacter.fighter,
                color: entrantOneCharacter.color,
                pose: entrantOneCharacter.pose,
              },
            ],
          },
          entrant_2: {
            tag: entrant.entrant_2.tag.trim(),
            characters: [
              {
                melee_fighter_name: entrantTwoCharacter.fighter,
                color: entrantTwoCharacter.color,
                pose: entrantTwoCharacter.pose,
              },
            ],
          },
        };
      }),
    }),
    [entrants, eventFormat, podiumSize, tournament],
  );

  function selectFormat(format: EventFormat) {
    const size = recommendedPodiumSize(format);
    setEventFormat(format);
    setPodiumSize(size);
    setEntrants((current) => createEntrants(size, format, current));
  }

  function selectPodiumSize(size: PodiumSize) {
    setPodiumSize(size);
    setEntrants((current) => createEntrants(size, eventFormat, current));
  }

  function fighterByName(name: string): FighterOption | undefined {
    return fighters.find((fighter) => fighter.name === name);
  }

  function updateSinglesEntrant(
    index: number,
    field: "tag" | "seed" | "placement",
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
    field: "team_name" | "seed" | "placement" | "team_color",
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

  function updateCharacter(
    index: number,
    side: "singles" | "entrant_1" | "entrant_2",
    field: "fighter" | "color" | "pose",
    value: string,
  ) {
    setEntrants((current) =>
      current.map((entrant, entrantIndex) => {
        if (entrantIndex !== index) return entrant;

        if (entrant.kind === "singles") {
          const character = entrant.characters[0] ?? createCharacterForm();
          if (field === "fighter") {
            const option = fighterByName(value)?.options[0];
            return {
              ...entrant,
              characters: [
                {
                  fighter: value,
                  color: option?.color ?? "",
                  pose: option?.pose ?? "",
                },
              ],
            };
          }

          if (field === "color") {
            const matchingOption = fighterByName(character.fighter)?.options.find(
              (option) => option.color === value,
            );
            return {
              ...entrant,
              characters: [
                {
                  ...character,
                  color: value,
                  pose: matchingOption?.pose ?? "",
                },
              ],
            };
          }

          return {
            ...entrant,
            characters: [{ ...character, pose: value }],
          };
        }

        const member = side === "entrant_1" ? entrant.entrant_1 : entrant.entrant_2;
        const character = member.characters[0] ?? createCharacterForm();

        if (field === "fighter") {
          const option = fighterByName(value)?.options[0];
          const nextMember = {
            ...member,
            characters: [
              {
                fighter: value,
                color: option?.color ?? "",
                pose: option?.pose ?? "",
              },
            ],
          };
          return side === "entrant_1"
            ? { ...entrant, entrant_1: nextMember }
            : { ...entrant, entrant_2: nextMember };
        }

        if (field === "color") {
          const matchingOption = fighterByName(character.fighter)?.options.find(
            (option) => option.color === value,
          );
          const nextMember = {
            ...member,
            characters: [
              {
                ...character,
                color: value,
                pose: matchingOption?.pose ?? "",
              },
            ],
          };
          return side === "entrant_1"
            ? { ...entrant, entrant_1: nextMember }
            : { ...entrant, entrant_2: nextMember };
        }

        const nextMember = {
          ...member,
          characters: [{ ...character, pose: value }],
        };

        return side === "entrant_1"
          ? { ...entrant, entrant_1: nextMember }
          : { ...entrant, entrant_2: nextMember };
      }),
    );
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
      ? result.entrants.slice(0, nextSize)
      : [];
    setEntrants((current) =>
      createEntrants(nextSize, nextFormat, current).map((existing, index) => {
        const imported = importedEntrants[index];
        if (!isRecord(imported)) return existing;

        const character = firstCharacter(imported);
        const importedCharacter = createCharacterForm(
          stringValue(
            imported.fighter,
            imported.melee_fighter_name,
            character.fighter,
            character.melee_fighter_name,
          ),
          stringValue(imported.color, character.color),
          stringValue(imported.pose, character.pose),
        );

        if (nextFormat === "singles") {
          return createSinglesEntrant(index + 1, {
            kind: "singles",
            tag:
              (stringValue(imported.tag, imported.name, imported.player_tag) ||
                (existing.kind === "singles" ? existing.tag : "")),
            seed:
              stringValue(imported.seed) ||
              (existing.kind === "singles" ? existing.seed : String(index + 1)),
            placement:
              stringValue(imported.placement, imported.rank) ||
              (existing.kind === "singles" ? existing.placement : String(index + 1)),
            characters: [importedCharacter],
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
          seed:
            stringValue(imported.seed) ||
            (existing.kind === "doubles" ? existing.seed : String(index + 1)),
          placement:
            stringValue(imported.placement, imported.rank) ||
            (existing.kind === "doubles" ? existing.placement : String(index + 1)),
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
      const result = await importBracket(bracketUrl.trim());
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

  const downloadName = `${tournament.title || "melee"}-podium`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  return (
    <main className="page-shell">
      <header className="site-header">
        <div>
          <p className="eyebrow">tyro.work</p>
          <h1>Melee Podium Maker</h1>
          <p className="lede">
            Enter a top three manually or import a public bracket, then render a
            downloadable podium graphic.
          </p>
        </div>
        <div className={`health health--${health}`} role="status">
          <span aria-hidden="true" />
          API {health}
        </div>
      </header>

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
            {isImporting ? "Importing�" : "Import"}
          </button>
        </form>
        {importState && <p className="form-message">{importState}</p>}
      </section>

      <form onSubmit={handleRender}>
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Podium format</h2>
              <p>Choose the event type and how many placements to render.</p>
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
              {([3, 4, 8] as const).filter((size) => eventFormat === "singles" || size !== 8).map((size) => (
                <label className="choice" key={size}>
                  <input type="radio" name="podium-size" checked={podiumSize === size} onChange={() => selectPodiumSize(size)} />
                  Top {size}
                </label>
              ))}
            </fieldset>
          </div>
        </section>

        <section className="panel">
          <h2>Tournament</h2>
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
              <h2>Top {podiumSize}</h2>
              <p>Character colors and poses come from the renderer.</p>
            </div>
            {optionsError && (
              <p className="error" role="alert">
                {optionsError}
              </p>
            )}
          </div>

          <div className="entrant-grid">
            {entrants.map((entrant, index) => {
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
                    <legend>Placement {index + 1}</legend>
                    <label>
                      Player tag
                      <input
                        value={entrant.tag}
                        onChange={(event) =>
                          updateSinglesEntrant(index, "tag", event.target.value)
                        }
                        placeholder={`Player ${index + 1}`}
                        required
                      />
                    </label>
                    <div className="row-fields">
                      <label>
                        Seed
                        <input
                          type="number"
                          min="1"
                          value={entrant.seed}
                          onChange={(event) =>
                            updateSinglesEntrant(index, "seed", event.target.value)
                          }
                        />
                      </label>
                      <label>
                        Placement
                        <input
                          type="number"
                          min="1"
                          value={entrant.placement}
                          onChange={(event) =>
                            updateSinglesEntrant(index, "placement", event.target.value)
                          }
                          required
                        />
                      </label>
                    </div>
                    <label>
                      Fighter
                      <select
                        value={character.fighter}
                        onChange={(event) =>
                          updateCharacter(index, "singles", "fighter", event.target.value)
                        }
                        required
                      >
                        <option value="">Choose a fighter</option>
                        {character.fighter &&
                          !fighters.some(
                            (option) => option.name === character.fighter,
                          ) && (
                            <option value={character.fighter}>{character.fighter}</option>
                          )}
                        {fighters.map((option) => (
                          <option key={option.name} value={option.name}>
                            {option.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="row-fields">
                      <label>
                        Color
                        <select
                          value={character.color}
                          onChange={(event) =>
                            updateCharacter(index, "singles", "color", event.target.value)
                          }
                          required
                        >
                          {character.color && !colors.includes(character.color) && (
                            <option value={character.color}>{character.color}</option>
                          )}
                          {colors.map((color) => (
                            <option key={color} value={color}>
                              {color}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Pose
                        <select
                          value={character.pose}
                          onChange={(event) =>
                            updateCharacter(index, "singles", "pose", event.target.value)
                          }
                          required
                        >
                          {character.pose && !poses.includes(character.pose) && (
                            <option value={character.pose}>{character.pose}</option>
                          )}
                          {poses.map((pose) => (
                            <option key={pose} value={pose}>
                              {pose}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
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
                  <legend>Placement {index + 1}</legend>
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
                  <div className="row-fields">
                    <label>
                      Seed
                      <input
                        type="number"
                        min="1"
                        value={entrant.seed}
                        onChange={(event) =>
                          updateDoublesTeam(index, "seed", event.target.value)
                        }
                      />
                    </label>
                    <label>
                      Placement
                      <input
                        type="number"
                        min="1"
                        value={entrant.placement}
                        onChange={(event) =>
                          updateDoublesTeam(index, "placement", event.target.value)
                        }
                        required
                      />
                    </label>
                  </div>
                  <label>
                    Team color
                    <select
                      value={entrant.team_color}
                      onChange={(event) =>
                        updateDoublesTeam(index, "team_color", event.target.value)
                      }
                    >
                      <option value="">None</option>
                      <option value="red">Red</option>
                      <option value="blue">Blue</option>
                      <option value="green">Green</option>
                    </select>
                  </label>

                  <div className="row-fields">
                    <label>
                      Entrant 1 tag
                      <input
                        value={entrant.entrant_1.tag}
                        onChange={(event) =>
                          updateEntrantTag(index, "entrant_1", event.target.value)
                        }
                        placeholder={`Player 1 ${index + 1}`}
                        required
                      />
                    </label>
                    <label>
                      Entrant 2 tag
                      <input
                        value={entrant.entrant_2.tag}
                        onChange={(event) =>
                          updateEntrantTag(index, "entrant_2", event.target.value)
                        }
                        placeholder={`Player 2 ${index + 1}`}
                        required
                      />
                    </label>
                  </div>

                  <div className="row-fields">
                    <fieldset className="entrant-card" style={{ padding: "0.75rem" }}>
                      <legend>Entrant 1</legend>
                      <label>
                        Fighter
                        <select
                          value={teamCharacterOne.fighter}
                          onChange={(event) =>
                            updateCharacter(index, "entrant_1", "fighter", event.target.value)
                          }
                          required
                        >
                          <option value="">Choose a fighter</option>
                          {teamCharacterOne.fighter &&
                            !fighters.some(
                              (option) => option.name === teamCharacterOne.fighter,
                            ) && (
                              <option value={teamCharacterOne.fighter}>
                                {teamCharacterOne.fighter}
                              </option>
                            )}
                          {fighters.map((option) => (
                            <option key={option.name} value={option.name}>
                              {option.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="row-fields">
                        <label>
                          Color
                          <select
                            value={teamCharacterOne.color}
                            onChange={(event) =>
                              updateCharacter(index, "entrant_1", "color", event.target.value)
                            }
                            required
                          >
                            {teamCharacterOne.color && !colorsOne.includes(teamCharacterOne.color) && (
                              <option value={teamCharacterOne.color}>{teamCharacterOne.color}</option>
                            )}
                            {colorsOne.map((color) => (
                              <option key={color} value={color}>
                                {color}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Pose
                          <select
                            value={teamCharacterOne.pose}
                            onChange={(event) =>
                              updateCharacter(index, "entrant_1", "pose", event.target.value)
                            }
                            required
                          >
                            {teamCharacterOne.pose && !posesOne.includes(teamCharacterOne.pose) && (
                              <option value={teamCharacterOne.pose}>{teamCharacterOne.pose}</option>
                            )}
                            {posesOne.map((pose) => (
                              <option key={pose} value={pose}>
                                {pose}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                    </fieldset>

                    <fieldset className="entrant-card" style={{ padding: "0.75rem" }}>
                      <legend>Entrant 2</legend>
                      <label>
                        Fighter
                        <select
                          value={teamCharacterTwo.fighter}
                          onChange={(event) =>
                            updateCharacter(index, "entrant_2", "fighter", event.target.value)
                          }
                          required
                        >
                          <option value="">Choose a fighter</option>
                          {teamCharacterTwo.fighter &&
                            !fighters.some(
                              (option) => option.name === teamCharacterTwo.fighter,
                            ) && (
                              <option value={teamCharacterTwo.fighter}>
                                {teamCharacterTwo.fighter}
                              </option>
                            )}
                          {fighters.map((option) => (
                            <option key={option.name} value={option.name}>
                              {option.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="row-fields">
                        <label>
                          Color
                          <select
                            value={teamCharacterTwo.color}
                            onChange={(event) =>
                              updateCharacter(index, "entrant_2", "color", event.target.value)
                            }
                            required
                          >
                            {teamCharacterTwo.color && !colorsTwo.includes(teamCharacterTwo.color) && (
                              <option value={teamCharacterTwo.color}>{teamCharacterTwo.color}</option>
                            )}
                            {colorsTwo.map((color) => (
                              <option key={color} value={color}>
                                {color}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Pose
                          <select
                            value={teamCharacterTwo.pose}
                            onChange={(event) =>
                              updateCharacter(index, "entrant_2", "pose", event.target.value)
                            }
                            required
                          >
                            {teamCharacterTwo.pose && !posesTwo.includes(teamCharacterTwo.pose) && (
                              <option value={teamCharacterTwo.pose}>{teamCharacterTwo.pose}</option>
                            )}
                            {posesTwo.map((pose) => (
                              <option key={pose} value={pose}>
                                {pose}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                    </fieldset>
                  </div>
                </fieldset>
              );
            })}
          </div>

          <details className="payload-preview">
            <summary>Preview API request</summary>
            <pre>{JSON.stringify(payload, null, 2)}</pre>
          </details>

          <div className="form-actions">
            <button className="button-primary" type="submit" disabled={isRendering}>
              {isRendering ? "Rendering�" : "Render podium"}
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
            >
              Download PNG
            </a>
          )}
        </div>
        <div className="preview-frame">
          {previewUrl ? (
            <img src={previewUrl} alt="Rendered tournament podium" />
          ) : (
            <p>Complete the form and select �Render podium.�</p>
          )}
        </div>
      </section>
    </main>
  );
}

export default App;
