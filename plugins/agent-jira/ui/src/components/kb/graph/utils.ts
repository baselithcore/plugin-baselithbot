/**
 * Brilliantly cleans text from markdown-like syntax or underscores.
 */
export const cleanText = (text: string): string => {
  if (!text) return '';
  return text
    .replace(/[#*_\[\]]/g, '')
    .replace(/_/g, ' ')
    .trim();
};
