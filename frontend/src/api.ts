export interface CharacterOption {
  color: string;
  pose: string;
}

export interface FighterOption {
  name: string;
  options: CharacterOption[];
}

export interface OptionsResponse {
  modes: string[];
  fighters: FighterOption[];
  team_colors: string[];
}

export interface HealthResponse {
  status?: string;
  [key: string]: unknown;
}

export interface StatsResponse {
  render_count: number;
}

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim();
const viteBase = import.meta.env.BASE_URL.endsWith("/")
  ? import.meta.env.BASE_URL
  : `${import.meta.env.BASE_URL}/`;
const rawApiBase = configuredBase || `${viteBase}api/`;
const apiBase = new URL(
  rawApiBase.endsWith("/") ? rawApiBase : `${rawApiBase}/`,
  window.location.origin,
);

/**
 * Builds URLs that work both on Vite's dev server and when the app is mounted
 * at /melee-podium-template/. VITE_API_BASE_URL can override the default.
 */
export function apiUrl(endpoint: string): string {
  return new URL(endpoint.replace(/^\/+/, ""), apiBase).toString();
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function errorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const body = (await response.json()) as {
      error?: string;
      message?: string;
      detail?: string;
    };
    return body.error || body.message || body.detail || response.statusText;
  }

  const text = await response.text();
  return text || response.statusText || `Request failed (${response.status})`;
}

export async function request(
  endpoint: string,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(apiUrl(endpoint), {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }

  return response;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await request("health");
  return (await response.json()) as HealthResponse;
}

export async function getStats(): Promise<StatsResponse> {
  const response = await request("stats");
  return (await response.json()) as StatsResponse;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

export async function getOptions(): Promise<OptionsResponse> {
  const response = await request("options");
  const body = (await response.json()) as Partial<OptionsResponse>;
  const fighters = Array.isArray(body.fighters)
    ? body.fighters
        .filter(
          (fighter): fighter is FighterOption =>
            typeof fighter === "object" &&
            fighter !== null &&
            typeof (fighter as FighterOption).name === "string",
        )
        .map((fighter) => ({
          name: fighter.name,
          options: Array.isArray(fighter.options)
            ? fighter.options.filter(
                (option): option is CharacterOption =>
                  typeof option === "object" &&
                  option !== null &&
                  typeof option.color === "string" &&
                  typeof option.pose === "string",
              )
            : [],
        }))
    : [];

  return {
    modes: asStringArray(body.modes),
    fighters,
    team_colors: asStringArray(body.team_colors),
  };
}

export async function importBracket(url: string): Promise<unknown> {
  const response = await request("import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return response.json() as Promise<unknown>;
}

export async function renderPodium(payload: unknown): Promise<Blob> {
  const response = await request("render", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "image/png, application/json",
    },
    body: JSON.stringify(payload),
  });
  const blob = await response.blob();

  if (!blob.type.toLowerCase().includes("image/png")) {
    throw new Error("The render endpoint did not return a PNG image.");
  }

  return blob;
}
