import { FormEvent, useMemo, useState } from "react";
import { importBracket } from "./api";
import {
  BracketImportReview,
  FavoriteImportCorrection,
  ImportedBracketCharacter,
  buildBracketReview,
  normalizeBracketImport,
} from "./bracket";
import { CharacterStockIcons } from "./FavoritePicker";
import { FavoritesData } from "./favorites";
import { EventFormat } from "./format";

interface BracketStepProps {
  url: string;
  review: BracketImportReview | null;
  favorites: FavoritesData;
  eventFormat: EventFormat;
  entrantCount: number;
  onUrlChange: (url: string) => void;
  onReviewChange: (review: BracketImportReview) => void;
  onSkip: () => void;
}

function providerName(provider: string): string {
  if (provider === "start.gg") return "Start.gg";
  if (provider === "challonge") return "Challonge";
  if (provider === "parry.gg") return "Parry.gg";
  return provider || "Bracket";
}

function ReviewParticipant({
  tag,
  characters,
  correction,
  onToggle,
}: {
  tag: string;
  characters: ImportedBracketCharacter[];
  correction?: FavoriteImportCorrection;
  onToggle: (correction: FavoriteImportCorrection) => void;
}) {
  const displayedTag = correction?.accepted ? correction.resolvedTag : tag;
  const displayedCharacters = correction?.accepted ? correction.favoriteCharacters : characters;
  return <div className={`bracket-participant${correction ? correction.accepted ? " is-corrected" : " is-reverted" : ""}`}>
    <div className="bracket-participant__identity">
      <div>
        {correction ? <><span className="bracket-participant__source">{tag}</span><span className="bracket-participant__arrow" aria-hidden="true">→</span></> : null}
        <strong>{displayedTag}</strong>
      </div>
      <CharacterStockIcons characters={displayedCharacters} />
    </div>
    {correction ? <div className="bracket-participant__match">
      <span>{correction.accepted ? `Using saved favorite “${correction.favoriteTag}”` : `Favorite suggestion “${correction.favoriteTag}” not applied`}</span>
      <button className="button button--outline" type="button" onClick={() => onToggle(correction)}>{correction.accepted ? "Use bracket entrant" : "Use favorite entrant"}</button>
    </div> : <small>No saved favorite match — using the bracket data.</small>}
  </div>;
}

export default function BracketStep({ url, review, favorites, eventFormat, entrantCount, onUrlChange, onReviewChange, onSkip }: BracketStepProps) {
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const acceptedCorrections = useMemo(() => review?.corrections.filter((item) => item.accepted).length ?? 0, [review]);

  async function handleImport(event: FormEvent) {
    event.preventDefault();
    setImporting(true);
    setMessage("");
    try {
      const response = normalizeBracketImport(await importBracket(url.trim(), entrantCount as 3 | 4 | 8), entrantCount);
      const nextReview = buildBracketReview(response, favorites, eventFormat);
      onReviewChange(nextReview);
      setMessageIsError(false);
      setMessage(nextReview.corrections.length
        ? `Bracket imported. ${nextReview.corrections.length} saved entrant ${nextReview.corrections.length === 1 ? "match was" : "matches were"} applied automatically.`
        : "Bracket imported. No saved entrant matches were found.");
    } catch (error) {
      setMessageIsError(true);
      setMessage(error instanceof Error ? error.message : "Bracket import failed.");
    } finally {
      setImporting(false);
    }
  }

  function toggleCorrection(selected: FavoriteImportCorrection) {
    if (!review) return;
    onReviewChange({
      ...review,
      corrections: review.corrections.map((item) => item.id === selected.id ? { ...item, accepted: !item.accepted } : item),
    });
  }

  return <section className="step-content bracket-step">
    <div className="step-intro"><div className="step-heading-row"><h1>Import a Bracket</h1><button className="button button--ghost" type="button" onClick={onSkip}>Skip bracket import</button></div><p>Import tournament data and placements automatically, or skip this optional step and enter them yourself.</p></div>
    <form className="bracket-import-card" onSubmit={handleImport}>
      <div className="bracket-import-card__heading"><span className="eyebrow">Public bracket link</span><h2>Bring in bracket results</h2><p>Supports Start.gg, Start.gg USB Reporting character data, Challonge.com, and Parry.gg brackets.</p></div>
      <label className="field bracket-url-field">Bracket URL<input type="url" value={url} onChange={(event) => onUrlChange(event.target.value)} placeholder="https://start.gg/tournament/.../event/..." required /></label>
      <div className="bracket-provider-list" aria-label="Supported bracket providers"><span>start.gg</span><span>USB Reporting</span><span>challonge.com</span><span>parry.gg</span></div>
      <button className="button button--dark bracket-import-button" type="submit" disabled={importing || !url.trim()}>{importing ? "Importing bracket…" : review ? "Import bracket again" : "Import bracket"}</button>
    </form>
    {message && <p className="inline-message format-message" role={messageIsError ? "alert" : "status"}>{message}</p>}

    {review && <section className="bracket-review" aria-labelledby="bracket-review-heading">
      <div className="bracket-review__heading"><div><span className="eyebrow">Imported results</span><h2 id="bracket-review-heading">{review.source.tournament.title || "Imported bracket"}</h2><p>{providerName(review.source.provider)}{review.source.tournament.event ? ` · ${review.source.tournament.event}` : ""} · {review.source.entrants.length} shown</p></div><span className="bracket-review__count">{acceptedCorrections} favorite {acceptedCorrections === 1 ? "match" : "matches"} active</span></div>
      <p className="bracket-review__explanation">Saved entrant matches are accepted automatically. Review each suggestion and use the bracket entrant when a match is not the one you want.</p>
      <div className="bracket-result-list">{review.source.entrants.map((entrant, entrantIndex) => {
        const entrantCorrection = review.corrections.find((item) => item.entrantIndex === entrantIndex && item.memberIndex === null);
        return <article className="bracket-result" key={`${entrant.placement ?? entrantIndex}-${entrant.tag}`}>
          <div className="bracket-result__place"><span>{entrant.placement ? `#${entrant.placement}` : `#${entrantIndex + 1}`}</span>{eventFormat === "doubles" && <strong>{entrant.tag}</strong>}{entrant.seed && <small>Seed {entrant.seed}</small>}</div>
          {eventFormat === "singles" ? <ReviewParticipant tag={entrant.tag} characters={entrant.characters} correction={entrantCorrection} onToggle={toggleCorrection} /> : entrant.members.length ? <div className="bracket-team-members">{entrant.members.map((member, memberIndex) => <ReviewParticipant key={`${member.tag}-${memberIndex}`} tag={member.tag} characters={member.characters} correction={review.corrections.find((item) => item.entrantIndex === entrantIndex && item.memberIndex === memberIndex)} onToggle={toggleCorrection} />)}</div> : <p className="bracket-result__missing">This provider supplied the team name but no individual member data. Add the team members in the Entrants step.</p>}
        </article>;
      })}</div>
    </section>}
  </section>;
}

