/**
 * Events service for seasonal events functionality.
 */

import type {
  ApiResponse,
  EventMonster,
  SeasonalEvent,
  UserEventProgress,
} from '@/domain/types';
import { api } from './api';

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
    return api.get('/events/active');
  },

  /**
   * Get all events (current and upcoming).
   */
  async getAllEvents(
    includePast: boolean = false
  ): Promise<ApiResponse<{ events: SeasonalEvent[] }>> {
    return api.get(`/events?include_past=${includePast}`);
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
    return api.get(`/events/${eventId}`);
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
    return api.get(`/events/${eventId}/progress`);
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
    return api.post('/admin/events', eventData);
  },
};

export default eventsService;
