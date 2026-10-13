/** Match the download suffix to the encoded preview rather than its canvas. */
export function previewDownloadName(title: string, mediaType: string): string {
  const safeTitle = title.trim().replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase();
  const extension = mediaType.split(";")[0].trim().toLowerCase() === "image/gif" ? "gif" : "png";
  return `${safeTitle || "melee-podium"}.${extension}`;
}
