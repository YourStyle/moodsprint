/**
 * Onboarding API service.
 */

import { api } from './api';
import type {
  UserProfile,
  OnboardingInput,
  OnboardingResponse,
} from '@/domain/types';

interface OnboardingStatusResponse {
  completed: boolean;
  profile: UserProfile | null;
}

interface ProfileResponse {
  profile: UserProfile;
}

export const onboardingService = {
  /**
   * Get onboarding status for current user.
   */
  async getStatus() {
    return api.get<OnboardingStatusResponse>('/onboarding/status');
  },

  /**
   * Complete onboarding with user responses.
   */
  async complete(input: OnboardingInput) {
    return api.post<OnboardingResponse>('/onboarding/complete', input);
  },

  /**
   * Get user's productivity profile.
   */
  async getProfile() {
    return api.get<ProfileResponse>('/onboarding/profile');
  },

  /**
   * Update profile settings.
   */
  async updateProfile(settings: {
    notifications_enabled?: boolean;
    daily_reminder_time?: string;
    preferred_session_duration?: number;
    work_start_time?: string;
    work_end_time?: string;
    work_days?: number[];
    timezone?: string;
  }) {
    return api.put<ProfileResponse>('/onboarding/profile', settings);
  },
};
