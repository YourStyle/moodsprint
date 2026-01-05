import { api } from './api';

export interface GenreStatus {
  users_count: number;
  active_templates: number;
  inactive_templates: number;
  total_templates: number;
  rarity_requirements: {
    [rarity: string]: {
      factor: number | null;
      required: number | string;
      needs_more: boolean;
    };
  };
}

export interface CardPoolStatus {
  genres: {
    [genre: string]: GenreStatus;
  };
}

export interface CardTemplate {
  id: number;
  name: string;
  description: string;
  genre: string;
  base_hp: number;
  base_attack: number;
  image_url: string | null;
  emoji: string;
  ai_generated: boolean;
  is_active: boolean;
  created_at: string | null;
}

export interface GenerationSchedule {
  genres: {
    [genre: string]: {
      users_count: number;
      templates_count: number;
      schedule: {
        [rarity: string]: {
          status: string;
          message: string;
          current?: number;
          required?: number;
          users_needed_for_next?: number;
          cards_needed?: number;
        };
      };
    };
  };
}

export interface AdminStats {
  total_users: number;
  total_templates: number;
  active_templates: number;
  total_user_cards: number;
  cards_by_rarity: { [rarity: string]: number };
  users_by_genre: { [genre: string]: number };
}

export const adminService = {
  async getCardPoolStatus(): Promise<CardPoolStatus> {
    const response = await api.get<CardPoolStatus>('/admin/card-pool');
    return response.data as CardPoolStatus;
  },

  async getGenreTemplates(genre: string): Promise<{ genre: string; templates: CardTemplate[]; total: number }> {
    const response = await api.get<{ genre: string; templates: CardTemplate[]; total: number }>(`/admin/card-pool/${genre}/templates`);
    return response.data as { genre: string; templates: CardTemplate[]; total: number };
  },

  async toggleTemplateActive(templateId: number): Promise<{ template_id: number; is_active: boolean; name: string }> {
    const response = await api.post<{ template_id: number; is_active: boolean; name: string }>(`/admin/card-pool/template/${templateId}/toggle`);
    return response.data as { template_id: number; is_active: boolean; name: string };
  },

  async generateTemplate(genre: string, options?: { rarity?: string; name?: string; description?: string }): Promise<{ template: CardTemplate }> {
    const response = await api.post<{ template: CardTemplate }>(`/admin/card-pool/${genre}/generate`, options || {});
    return response.data as { template: CardTemplate };
  },

  async generateTemplateImage(templateId: number): Promise<{ template_id: number; image_url: string; already_exists?: boolean }> {
    const response = await api.post<{ template_id: number; image_url: string; already_exists?: boolean }>(`/admin/card-pool/template/${templateId}/generate-image`);
    return response.data as { template_id: number; image_url: string; already_exists?: boolean };
  },

  async getGenerationSchedule(): Promise<GenerationSchedule> {
    const response = await api.get<GenerationSchedule>('/admin/card-pool/generation-schedule');
    return response.data as GenerationSchedule;
  },

  async getAdminStats(): Promise<AdminStats> {
    const response = await api.get<AdminStats>('/admin/stats');
    return response.data as AdminStats;
  },
};
