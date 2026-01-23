export function slugify(text) {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/[().]/g, '') 
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function formatDate(dateString, format = {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }) {
  if (!dateString) return "";
  
  const date = new Date(dateString);
  
  return new Intl.DateTimeFormat('en-GB', format).format(date);
}