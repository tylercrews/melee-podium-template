import { FighterOption } from "./api";
import { FavoriteCharacter } from "./favorites";

export function createCharacterForm(fighter = "", color = "", pose = ""): FavoriteCharacter {
  return { fighter, color, pose };
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
  const updateCharacter = (characterIndex: number, field: "fighter" | "color" | "pose", value: string) => {
    onChange(characters.map((character, currentIndex) => {
      if (currentIndex !== characterIndex) return character;
      if (field === "fighter") {
        const option = fighters.find((fighter) => fighter.name === value)?.options[0];
        return { fighter: value, color: option?.color ?? "", pose: "" };
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
      const poses = unique(orderedOptions.filter((option) => !character.color || option.color === character.color).map((option) => option.pose));
      const availableFighters = fighters.filter((option) => option.name === character.fighter || !selectedFighters.has(option.name));
      return <fieldset className="character-fields__item" key={characterIndex}>
        <legend>Fighter {characterIndex + 1}</legend>
        {characters.length > 1 && <button type="button" className="button-danger" onClick={() => onChange(characters.filter((_, index) => index !== characterIndex))}>Remove fighter</button>}
        <label>Fighter<select value={character.fighter} onChange={(event) => updateCharacter(characterIndex, "fighter", event.target.value)} required><option value="">Choose a fighter</option>{character.fighter && !fighters.some((option) => option.name === character.fighter) && <option value={character.fighter}>{character.fighter}</option>}{availableFighters.map((option) => <option key={option.name} value={option.name}>{option.name}</option>)}</select></label>
        <div className="row-fields">
          <label>Color<select value={character.color} onChange={(event) => updateCharacter(characterIndex, "color", event.target.value)}><option value="">Random</option>{character.color && !colors.includes(character.color) && <option value={character.color}>{character.color}</option>}{colors.map((color) => <option key={color} value={color}>{color}</option>)}</select></label>
          <label>Pose<select value={character.pose} onChange={(event) => updateCharacter(characterIndex, "pose", event.target.value)}><option value="">Random</option>{character.pose && !poses.includes(character.pose) && <option value={character.pose}>{character.pose}</option>}{poses.map((pose) => <option key={pose} value={pose}>{pose}</option>)}</select></label>
        </div>
      </fieldset>;
    })}
    <button type="button" onClick={() => onChange([...characters, createCharacterForm()])} disabled={characters.length >= fighters.length}>Add fighter</button>
  </div>;
}