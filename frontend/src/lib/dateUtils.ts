import type { TranslationKey } from '@/lib/i18n';

/**
 * Formats a Date to a YYYY-MM-DD string using the local timezone.
 * Avoids toISOString() which converts to UTC and can shift dates.
 */
export const formatDateForAPI = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * Formats a Date for human-readable display.
 * Returns localised "today" / "tomorrow" / "yesterday" labels when applicable,
 * otherwise falls back to a long locale date string.
 */
export const formatDateDisplay = (
  date: Date,
  language: 'ru' | 'en',
  t: (key: TranslationKey) => string,
): string => {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (formatDateForAPI(date) === formatDateForAPI(today)) return t('today');
  if (formatDateForAPI(date) === formatDateForAPI(tomorrow)) return t('tomorrow');
  if (formatDateForAPI(date) === formatDateForAPI(yesterday)) return t('yesterday');

  const locale = language === 'ru' ? 'ru-RU' : 'en-US';
  return date.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long' });
};

/**
 * Calculates the number of elapsed seconds for an active focus session.
 * Uses the session's started_at timestamp compared to now.
 */
export const calculateElapsedSeconds = (startedAt: string): number => {
  const start = new Date(startedAt).getTime();
  const now = Date.now();
  return Math.floor((now - start) / 1000);
};
