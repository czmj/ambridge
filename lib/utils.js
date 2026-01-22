export function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[().]/g, '') 
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}