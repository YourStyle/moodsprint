/**
 * Events service for seasonal events functionality.
 */

import type {
  ApiResponse,
  EventMonster,
  SeasonalEvent,
  UserEventProgress,
} from '@/domain/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = localStorage.getItem('token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  return response.json();
}

export const eventsService = {
  /**
   * Get currently active event with user progress.
   */
  async getActiveEvent(): Promise<
    ApiResponse<{
      event: SeasonalEvent | null;
      progress: UserEventProgress | null;
      monsters: EventMonster[];
    }>
  > {
    return fetchWithAuth('/events/active');
  },

  /**
   * Get all events (current and upcoming).
   */
  async getAllEvents(
    includePast: boolean = false
  ): Promise<ApiResponse<{ events: SeasonalEvent[] }>> {
    return fetchWithAuth(`/events?include_past=${includePast}`);
  },

  /**
   * Get detailed information about a specific event.
   */
  async getEventDetails(eventId: number): Promise<
    ApiResponse<{
      event: SeasonalEvent;
      progress: UserEventProgress | null;
      monsters: EventMonster[];
    }>
  > {
    return fetchWithAuth(`/events/${eventId}`);
  },

  /**
   * Get user's progress in a specific event.
   */
  async getEventProgress(eventId: number): Promise<
    ApiResponse<{
      event: SeasonalEvent;
      progress: UserEventProgress;
    }>
  > {
    return fetchWithAuth(`/events/${eventId}/progress`);
  },

  /**
   * Create a manual event (admin only).
   */
  async createManualEvent(eventData: {
    code: string;
    name: string;
    description?: string;
    start_date: string;
    end_date: string;
    emoji?: string;
    theme_color?: string;
    xp_multiplier?: number;
  }): Promise<
    ApiResponse<{
      event: SeasonalEvent;
      message: string;
    }>
  > {
    return fetchWithAuth('/admin/events', {
      method: 'POST',
      body: JSON.stringify(eventData),
    });
  },
};

export default eventsService;
