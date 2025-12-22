/**
 * Tasks service.
 */

import { api } from './api';
import type {
  Task,
  Subtask,
  CreateTaskInput,
  UpdateTaskInput,
  UpdateSubtaskInput,
  TaskSuggestion,
  ApiResponse,
  XPReward,
} from '@/domain/types';

interface TasksListResponse {
  tasks: Task[];
  total: number;
}

interface TaskResponse {
  task: Task;
}

// Card type for earned cards
interface CardEarned {
  id: number;
  name: string;
  description: string;
  genre: string;
  rarity: string;
  hp: number;
  attack: number;
  emoji: string;
  image_url?: string | null;
}

interface TaskWithXP extends TaskResponse, Partial<XPReward> {
  card_earned?: CardEarned;
  quick_completion?: boolean;
  quick_completion_message?: string;
}

interface SubtaskResponse {
  subtask: Subtask;
}

interface SubtaskWithXP extends SubtaskResponse, Partial<XPReward> {
  card_earned?: CardEarned;
  quick_completion?: boolean;
  quick_completion_message?: string;
}

interface DecomposeResponse {
  subtasks: Subtask[];
  strategy: string;
  message: string;
  no_new_steps?: boolean;
}

interface PostponeStatusResponse {
  has_postponed: boolean;
  tasks_postponed: number;
  priority_changes: Array<{
    task_id: number;
    task_title: string;
    old_priority: string;
    new_priority: string;
    postponed_count: number;
  }>;
  message: string | null;
}

interface SuggestionsResponse {
  suggestions: TaskSuggestion[];
  available_minutes: number;
  suggestions_count: number;
}

export const tasksService = {
  async getPostponeStatus(): Promise<ApiResponse<PostponeStatusResponse>> {
    return api.get<PostponeStatusResponse>('/tasks/postpone-status');
  },

  async getTasks(params?: {
    status?: string;
    due_date?: string;
    due_date_from?: string;
    due_date_to?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<TasksListResponse>> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.due_date) searchParams.set('due_date', params.due_date);
    if (params?.due_date_from) searchParams.set('due_date_from', params.due_date_from);
    if (params?.due_date_to) searchParams.set('due_date_to', params.due_date_to);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return api.get<TasksListResponse>(`/tasks${query ? `?${query}` : ''}`);
  },

  async getTask(taskId: number): Promise<ApiResponse<TaskResponse>> {
    return api.get<TaskResponse>(`/tasks/${taskId}`);
  },

  async createTask(input: CreateTaskInput): Promise<ApiResponse<TaskResponse>> {
    return api.post<TaskResponse>('/tasks', input);
  },

  async updateTask(taskId: number, input: UpdateTaskInput): Promise<ApiResponse<TaskWithXP>> {
    return api.put<TaskWithXP>(`/tasks/${taskId}`, input);
  },

  async deleteTask(taskId: number): Promise<ApiResponse<void>> {
    return api.delete<void>(`/tasks/${taskId}`);
  },

  async decomposeTask(taskId: number, moodId?: number): Promise<ApiResponse<DecomposeResponse>> {
    return api.post<DecomposeResponse>(`/tasks/${taskId}/decompose`, {
      mood_id: moodId,
    });
  },

  async createSubtask(
    taskId: number,
    input: { title: string; estimated_minutes?: number }
  ): Promise<ApiResponse<SubtaskResponse>> {
    return api.post<SubtaskResponse>(`/tasks/${taskId}/subtasks`, input);
  },

  async updateSubtask(
    subtaskId: number,
    input: UpdateSubtaskInput
  ): Promise<ApiResponse<SubtaskWithXP>> {
    return api.put<SubtaskWithXP>(`/subtasks/${subtaskId}`, input);
  },

  async reorderSubtasks(taskId: number, subtaskIds: number[]): Promise<ApiResponse<void>> {
    return api.post<void>('/subtasks/reorder', {
      task_id: taskId,
      subtask_ids: subtaskIds,
    });
  },

  async getSuggestions(availableMinutes: number): Promise<ApiResponse<SuggestionsResponse>> {
    return api.get<SuggestionsResponse>(`/tasks/suggestions?available_minutes=${availableMinutes}`);
  },
};
