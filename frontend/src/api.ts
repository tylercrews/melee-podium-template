export interface CharacterOption {
  color: string;
  pose: string;
  pose_label?: string;
  color_order?: number;
  portrait?: string;
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

export async function recordDownload(): Promise<StatsResponse> {
  const response = await request("download", { method: "POST" });
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

export async function importBracket(url: string, topEntrants: 3 | 4 | 8): Promise<unknown> {
  const response = await request("import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, top_entrants: topEntrants }),
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

export type UserImageCategory = "tournament_logo" | "background";

export interface UserImage {
  id: string;
  name: string;
  category: UserImageCategory;
  contentType: string;
  width: number;
  height: number;
  sizeBytes: number;
  createdAt?: string;
}

export interface BuiltInBackground {
  asset_id: string;
  size: { width: number; height: number };
}

export interface ProvidedFont {
  asset_id: string;
  name: string;
  size_adjustment: number;
}

export interface UserFont {
  id: string;
  name: string;
  contentType: string;
  sizeBytes: number;
  createdAt?: string;
}

export interface SavedFormat {
  id: string;
  name: string;
  schemaVersion: number;
  data: unknown;
  createdAt?: string;
  updatedAt?: string;
}

export async function listBuiltInBackgrounds(): Promise<BuiltInBackground[]> {
  const response = await request("backgrounds");
  const body = (await response.json()) as { items?: BuiltInBackground[] };
  return Array.isArray(body.items) ? body.items : [];
}

export function builtInBackgroundUrl(assetId: string): string {
  return apiUrl(`backgrounds/${encodeURIComponent(assetId)}`);
}

export async function listProvidedFonts(): Promise<ProvidedFont[]> {
  const response = await request("fonts");
  const body = (await response.json()) as { items?: ProvidedFont[] };
  return Array.isArray(body.items) ? body.items : [];
}

export function providedFontUrl(assetId: string): string {
  return apiUrl(`fonts/${encodeURIComponent(assetId)}`);
}

async function authenticatedRequest(endpoint: string, token: string, init?: RequestInit): Promise<Response> {
  return request(endpoint, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, ...init?.headers },
  });
}

export async function listSavedFormats(token: string): Promise<SavedFormat[]> {
  const response = await authenticatedRequest("firebase/layouts?limit=100", token);
  const body = (await response.json()) as { items?: SavedFormat[] };
  return Array.isArray(body.items) ? body.items : [];
}

export async function createSavedFormat(token: string, name: string, data: object): Promise<SavedFormat> {
  const response = await authenticatedRequest("firebase/layouts", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, data }),
  });
  return (await response.json()) as SavedFormat;
}

export async function replaceSavedFormat(token: string, id: string, name: string, data: object): Promise<SavedFormat> {
  const response = await authenticatedRequest(`firebase/layouts/${encodeURIComponent(id)}`, token, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, data }),
  });
  return (await response.json()) as SavedFormat;
}

export async function listUserImages(token: string): Promise<UserImage[]> {
  const response = await authenticatedRequest("firebase/images?limit=100", token);
  const body = (await response.json()) as { items?: UserImage[] };
  return Array.isArray(body.items)
    ? body.items.filter((image) => image.category === "tournament_logo" || image.category === "background")
    : [];
}

export async function uploadUserImage(token: string, file: File, name: string, category: UserImageCategory): Promise<UserImage> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  form.append("category", category);
  const response = await authenticatedRequest("firebase/images", token, { method: "POST", body: form });
  return (await response.json()) as UserImage;
}

export async function deleteUserImage(token: string, imageId: string): Promise<void> {
  await authenticatedRequest(`firebase/images/${encodeURIComponent(imageId)}`, token, { method: "DELETE" });
}

export async function getUserImageUrl(token: string, imageId: string): Promise<string> {
  const response = await authenticatedRequest(
    `firebase/images/${encodeURIComponent(imageId)}/download-url`,
    token,
    { method: "POST" },
  );
  const body = (await response.json()) as { url?: string };
  if (!body.url) throw new Error("The image preview URL was missing.");
  return body.url;
}

export async function listUserFonts(token: string): Promise<UserFont[]> {
  const response = await authenticatedRequest("firebase/fonts?limit=100", token);
  const body = (await response.json()) as { items?: UserFont[] };
  return Array.isArray(body.items) ? body.items : [];
}

export async function uploadUserFont(token: string, file: File, name: string): Promise<UserFont> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  const response = await authenticatedRequest("firebase/fonts", token, { method: "POST", body: form });
  return (await response.json()) as UserFont;
}

export async function deleteUserFont(token: string, fontId: string): Promise<void> {
  await authenticatedRequest(`firebase/fonts/${encodeURIComponent(fontId)}`, token, { method: "DELETE" });
}

export async function getUserFontUrl(token: string, fontId: string): Promise<string> {
  const response = await authenticatedRequest(`firebase/fonts/${encodeURIComponent(fontId)}/download-url`, token, { method: "POST" });
  const body = (await response.json()) as { url?: string };
  if (!body.url) throw new Error("The font preview URL was missing.");
  return body.url;
}
