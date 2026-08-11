import { useId, useState } from "react";
import { FighterOption } from "./api";
import { FavoriteCharacter } from "./favorites";

export function createCharacterForm(fighter = "", color = "", pose = "", mirrorHorizontally = false): FavoriteCharacter {
  return { fighter, color, pose, mirrorHorizontally };
}

const FALLBACK_COLOR_ORDER = ["default", "red", "green", "blue", "black", "white", "yellow", "pink", "purple", "cyan"];

function colorOrder(color: string, suppliedOrder?: number): number {
  if (suppliedOrder !== undefined) return suppliedOrder;
  const fallbackOrder = FALLBACK_COLOR_ORDER.indexOf(color.toLowerCase());
  return fallbackOrder === -1 ? FALLBACK_COLOR_ORDER.length : fallbackOrder;
}
function unique(values: string[]): string[] {
  return [...new Set(values)];
}

export default function EntrantCharacterEditor({ tag, tagLabel = "Player tag", tagPlaceholder, characters, fighters, onTagChange, onChange }: { tag: string; tagLabel?: string; tagPlaceholder?: string; characters: FavoriteCharacter[]; fighters: FighterOption[]; onTagChange: (tag: string) => void; onChange: (characters: FavoriteCharacter[]) => void }) {
  const selectedFighters = new Set(characters.map((character) => character.fighter).filter(Boolean));
  const [openFighterMenu, setOpenFighterMenu] = useState<number | null>(null);
  const fighterMenuId = useId();
  const updateCharacter = (characterIndex: number, field: "fighter" | "color" | "pose", value: string) => {
    onChange(characters.map((character, currentIndex) => {
      if (currentIndex !== characterIndex) return character;
      if (field === "fighter") {
        const option = fighters.find((fighter) => fighter.name === value)?.options[0];
        return { fighter: value, color: option?.color ?? "", pose: "", mirrorHorizontally: character.mirrorHorizontally === true };
      }
      if (field === "color") {
        return { ...character, color: value, pose: "" };
      }
      return { ...character, pose: value };
    }));
  };

  return <div className="character-fields">
    <label>{tagLabel}<input value={tag} onChange={(event) => onTagChange(event.target.value)} placeholder={tagPlaceholder} required /></label>
    {characters.map((character, characterIndex) => {
      const fighter = fighters.find((item) => item.name === character.fighter);
      const orderedOptions = [...(fighter?.options ?? [])].sort((left, right) => colorOrder(left.color, left.color_order) - colorOrder(right.color, right.color_order) || left.pose.localeCompare(right.pose));
      const colors = unique(orderedOptions.map((option) => option.color));
      const poseOptions = orderedOptions.filter((option) => !character.color || option.color === character.color).filter((option, index, options) => options.findIndex((candidate) => candidate.pose === option.pose) === index);
      const availableFighters = fighters.filter((option) => option.name === character.fighter || !selectedFighters.has(option.name));
      const previewPortrait = orderedOptions.find((option) => option.color === character.color && option.pose === character.pose);
      const previewUrl = previewPortrait?.portrait
        ? `${import.meta.env.BASE_URL}char_assets/renders/${encodeURIComponent(character.fighter)}/${encodeURIComponent(previewPortrait.portrait)}`
        : undefined;
      return <fieldset className="character-fields__item" key={characterIndex}>
        <legend>Fighter {characterIndex + 1}</legend>
        {characters.length > 1 && <button type="button" className="button-danger" onClick={() => onChange(characters.filter((_, index) => index !== characterIndex))}>Remove fighter</button>}
        <div className={previewUrl ? "character-fields__content character-fields__content--with-preview" : "character-fields__content"}>
          <div className="character-fields__controls">
            <label>Fighter<div className="fighter-combobox"><input value={character.fighter} onChange={(event) => { updateCharacter(characterIndex, "fighter", event.target.value); setOpenFighterMenu(characterIndex); }} onFocus={() => setOpenFighterMenu(characterIndex)} onBlur={() => { setOpenFighterMenu(null); if (character.fighter && !fighters.some((option) => option.name === character.fighter)) updateCharacter(characterIndex, "fighter", ""); }} onKeyDown={(event) => { if (event.key === "Escape") setOpenFighterMenu(null); if (event.key === "ArrowDown") setOpenFighterMenu(characterIndex); }} role="combobox" aria-autocomplete="list" aria-controls={`${fighterMenuId}-${characterIndex}`} aria-expanded={openFighterMenu === characterIndex} placeholder="Search fighters" title="Choose an exact fighter name from the list." required />{openFighterMenu === characterIndex && <ul className="fighter-combobox__menu" id={`${fighterMenuId}-${characterIndex}`} role="listbox">{availableFighters.filter((option) => option.name.toLowerCase().includes(character.fighter.toLowerCase())).map((option) => <li key={option.name} role="option" aria-selected={option.name === character.fighter}><button type="button" onMouseDown={(event) => { event.preventDefault(); updateCharacter(characterIndex, "fighter", option.name); setOpenFighterMenu(null); }}>{option.name}</button></li>)}</ul>}</div></label>
            <div className="row-fields">
              <label>Color<select value={character.color} onChange={(event) => updateCharacter(characterIndex, "color", event.target.value)}><option value="">Random</option>{character.color && !colors.includes(character.color) && <option value={character.color}>{character.color}</option>}{colors.map((color) => <option key={color} value={color}>{color}</option>)}</select></label>
              <label>Pose<select value={character.pose} onChange={(event) => updateCharacter(characterIndex, "pose", event.target.value)}><option value="">Random</option>{character.pose && !poseOptions.some((option) => option.pose === character.pose) && <option value={character.pose}>{character.pose}</option>}{poseOptions.map((option) => <option key={option.pose} value={option.pose}>{option.pose_label ?? option.pose}</option>)}</select></label>
            </div>
            <label className="choice"><input type="checkbox" checked={character.mirrorHorizontally === true} onChange={(event) => onChange(characters.map((item, index) => index === characterIndex ? { ...item, mirrorHorizontally: event.target.checked } : item))} /> Mirror Horizontally</label>
          </div>
          {previewUrl && <figure className="character-preview"><img className={character.mirrorHorizontally ? "character-preview__image--mirrored" : undefined} src={previewUrl} alt={`${character.color} ${character.pose} ${character.fighter} portrait`} /><figcaption>Selected portrait preview</figcaption></figure>}
        </div>
      </fieldset>;
    })}
    <button type="button" onClick={() => onChange([...characters, createCharacterForm()])} disabled={characters.length >= fighters.length}>Add fighter</button>
  </div>;
}
