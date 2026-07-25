import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  FighterOption,
  getHealth,
  getOptions,
  importBracket,
  renderPodium,
} from "./api";

interface EntrantForm {
  tag: string;
  seed: string;
  placement: string;
  fighter: string;
  color: string;
  pose: string;
}

interface TournamentForm {
  title: string;
  date: string;
  entrantsCount: string;
}

type EventFormat = "singles" | "doubles";
type PodiumSize = 3 | 4 | 8;

function createEntrants(count: number, existing: EntrantForm[] = []): EntrantForm[] {
  return Array.from({ length: count }, (_, index) => {
    const placement = index + 1;
    return existing[index] ?? {
      tag: "",
      seed: String(placement),
      placement: String(placement),
      fighter: "",
      color: "",
      pose: "",
    };
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
  });
const [eventFormat, setEventFormat] = useState<EventFormat>("singles");
  const [podiumSize, setPodiumSize] = useState<PodiumSize>(8);
  const [entrants, setEntrants] = useState<EntrantForm[]>(() => createEntrants(8));
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
            current.map((entrant) =>
              entrant.fighter
                ? entrant
                : {
                    ...entrant,
                    fighter: first.name,
                    color: firstOption?.color ?? "",
                    pose: firstOption?.pose ?? "",
                  },
            ),
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
      },
      entrants: entrants.map((entrant) => ({
        tag: entrant.tag.trim(),
        seed: entrant.seed ? Number(entrant.seed) : null,
        placement: Number(entrant.placement),
        fighter: entrant.fighter,
        color: entrant.color,
        pose: entrant.pose,
      })),
    }),
    [entrants, eventFormat, podiumSize, tournament],
  );

  function selectFormat(format: EventFormat) {
    const size = recommendedPodiumSize(format);
    setEventFormat(format);
    setPodiumSize(size);
    setEntrants((current) => createEntrants(size, current));
  }

  function selectPodiumSize(size: PodiumSize) {
    setPodiumSize(size);
    setEntrants((current) => createEntrants(size, current));
  }

  function fighterByName(name: string): FighterOption | undefined {
    return fighters.find((fighter) => fighter.name === name);
  }

  function updateEntrant(
    index: number,
    field: keyof EntrantForm,
    value: string,
  ) {
    setEntrants((current) =>
      current.map((entrant, entrantIndex) => {
        if (entrantIndex !== index) return entrant;
        if (field !== "fighter") return { ...entrant, [field]: value };

        const option = fighterByName(value)?.options[0];
        return {
          ...entrant,
          fighter: value,
          color: option?.color ?? "",
          pose: option?.pose ?? "",
        };
      }),
    );
  }

  function updateColor(index: number, color: string) {
    setEntrants((current) =>
      current.map((entrant, entrantIndex) => {
        if (entrantIndex !== index) return entrant;
        const matchingOption = fighterByName(entrant.fighter)?.options.find(
          (option) => option.color === color,
        );
        return {
          ...entrant,
          color,
          pose: matchingOption?.pose ?? "",
        };
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

    setEventFormat(nextFormat);
    setPodiumSize(nextSize);
    setTournament((current) => ({
      title:
        stringValue(
          importedTournament.title,
          importedTournament.name,
          result.title,
        ) || current.title,
      date:
        stringValue(importedTournament.date, result.date).slice(0, 10) ||
        current.date,
      entrantsCount:
        stringValue(
          importedTournament.entrants_count,
          importedTournament.entrant_count,
          result.entrants_count,
        ) || current.entrantsCount,
    }));

    const importedEntrants = Array.isArray(result.entrants)
      ? result.entrants.slice(0, nextSize)
      : [];
    setEntrants((current) =>
      createEntrants(nextSize, current).map((existing, index) => {
          const imported = importedEntrants[index];
          if (!isRecord(imported)) return existing;
          const character = firstCharacter(imported);
          return {
            tag:
              stringValue(imported.tag, imported.name, imported.player_tag) ||
              existing.tag,
            seed: stringValue(imported.seed) || existing.seed,
            placement:
              stringValue(imported.placement, imported.rank) ||
              existing.placement,
            fighter:
              stringValue(
                imported.fighter,
                imported.melee_fighter_name,
                character.fighter,
                character.melee_fighter_name,
              ) || existing.fighter,
            color:
              stringValue(imported.color, character.color) || existing.color,
            pose: stringValue(imported.pose, character.pose) || existing.pose,
          };
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
            {isImporting ? "Importing…" : "Import"}
          </button>
        </form>
        {importState && <p className="form-message">{importState}</p>}
      </section>

      <form onSubmit={handleRender}>
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
          </div>
        </section>

        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Podium format</h2>
              <p>Choose the event type and how many placements to render.</p>
            </div>
          </div>
          <div className="format-controls">
            <fieldset className="choice-group">
              <legend>Event type</legend>
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
              const fighter = fighterByName(entrant.fighter);
              const colors = unique(
                (fighter?.options ?? []).map((option) => option.color),
              );
              const poses = unique(
                (fighter?.options ?? [])
                  .filter((option) => option.color === entrant.color)
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
                        updateEntrant(index, "tag", event.target.value)
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
                          updateEntrant(index, "seed", event.target.value)
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
                          updateEntrant(index, "placement", event.target.value)
                        }
                        required
                      />
                    </label>
                  </div>
                  <label>
                    Fighter
                    <select
                      value={entrant.fighter}
                      onChange={(event) =>
                        updateEntrant(index, "fighter", event.target.value)
                      }
                      required
                    >
                      <option value="">Choose a fighter</option>
                      {entrant.fighter &&
                        !fighters.some(
                          (option) => option.name === entrant.fighter,
                        ) && (
                          <option value={entrant.fighter}>
                            {entrant.fighter}
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
                        value={entrant.color}
                        onChange={(event) =>
                          updateColor(index, event.target.value)
                        }
                        required
                      >
                        {entrant.color && !colors.includes(entrant.color) && (
                          <option value={entrant.color}>{entrant.color}</option>
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
                        value={entrant.pose}
                        onChange={(event) =>
                          updateEntrant(index, "pose", event.target.value)
                        }
                        required
                      >
                        {entrant.pose && !poses.includes(entrant.pose) && (
                          <option value={entrant.pose}>{entrant.pose}</option>
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
            })}
          </div>

          <details className="payload-preview">
            <summary>Preview API request</summary>
            <pre>{JSON.stringify(payload, null, 2)}</pre>
          </details>

          <div className="form-actions">
            <button className="button-primary" type="submit" disabled={isRendering}>
              {isRendering ? "Rendering…" : "Render podium"}
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
            <p>Complete the form and select “Render podium.”</p>
          )}
        </div>
      </section>
    </main>
  );
}

export default App;
