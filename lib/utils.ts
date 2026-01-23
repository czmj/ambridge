export function formatDate(dateString: string, format: Intl.DateTimeFormatOptions = {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }) {
  if (!dateString) return "";
  
  const date = new Date(dateString);
  
  return new Intl.DateTimeFormat('en-GB', format).format(date);
}