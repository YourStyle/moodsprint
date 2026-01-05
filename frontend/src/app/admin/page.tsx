'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  Settings,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Image,
  Plus,
  ToggleLeft,
  ToggleRight,
  Users,
  Layers,
  AlertCircle,
  CheckCircle,
  Clock,
  Sparkles,
} from 'lucide-react';
import { Card, Button } from '@/components/ui';
import { adminService, CardTemplate } from '@/services/admin';
import { cn } from '@/lib/utils';

const GENRES = ['magic', 'fantasy', 'scifi', 'cyberpunk', 'anime'];
const RARITIES = ['common', 'uncommon', 'rare', 'epic', 'legendary'];

const GENRE_LABELS: Record<string, string> = {
  magic: 'Магия',
  fantasy: 'Фэнтези',
  scifi: 'Sci-Fi',
  cyberpunk: 'Киберпанк',
  anime: 'Аниме',
};

const RARITY_LABELS: Record<string, string> = {
  common: 'Обычная',
  uncommon: 'Необычная',
  rare: 'Редкая',
  epic: 'Эпическая',
  legendary: 'Легендарная',
};

const RARITY_COLORS: Record<string, string> = {
  common: 'text-gray-400',
  uncommon: 'text-green-400',
  rare: 'text-blue-400',
  epic: 'text-purple-400',
  legendary: 'text-amber-400',
};

export default function AdminPage() {
  const queryClient = useQueryClient();
  const [expandedGenre, setExpandedGenre] = useState<string | null>(null);
  const [generatingFor, setGeneratingFor] = useState<{ genre: string; rarity: string } | null>(null);

  // Fetch card pool status
  const { data: poolStatus, isLoading: poolLoading } = useQuery({
    queryKey: ['admin', 'card-pool'],
    queryFn: () => adminService.getCardPoolStatus(),
  });

  // Fetch generation schedule
  const { data: schedule, isLoading: scheduleLoading } = useQuery({
    queryKey: ['admin', 'generation-schedule'],
    queryFn: () => adminService.getGenerationSchedule(),
  });

  // Fetch admin stats
  const { data: stats } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () => adminService.getAdminStats(),
  });

  // Fetch templates for expanded genre
  const { data: templatesData, isLoading: templatesLoading } = useQuery({
    queryKey: ['admin', 'templates', expandedGenre],
    queryFn: () => expandedGenre ? adminService.getGenreTemplates(expandedGenre) : null,
    enabled: !!expandedGenre,
  });

  // Toggle template mutation
  const toggleMutation = useMutation({
    mutationFn: (templateId: number) => adminService.toggleTemplateActive(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin'] });
    },
  });

  // Generate template mutation
  const generateMutation = useMutation({
    mutationFn: ({ genre, rarity }: { genre: string; rarity: string }) =>
      adminService.generateTemplate(genre, { rarity }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin'] });
      setGeneratingFor(null);
    },
    onError: () => {
      setGeneratingFor(null);
    },
  });

  // Generate image mutation
  const generateImageMutation = useMutation({
    mutationFn: (templateId: number) => adminService.generateTemplateImage(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'templates'] });
    },
  });

  const handleGenerate = (genre: string, rarity: string) => {
    setGeneratingFor({ genre, rarity });
    generateMutation.mutate({ genre, rarity });
  };

  if (poolLoading || scheduleLoading) {
    return (
      <div className="p-4 flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 pb-24 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-8 h-8 text-purple-500" />
        <div>
          <h1 className="text-xl font-bold text-white">Админ-панель</h1>
          <p className="text-sm text-gray-400">Управление пулом карт</p>
        </div>
      </div>

      {/* Stats Overview */}
      {stats && (
        <Card className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 border-purple-500/30">
          <div className="p-4">
            <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Общая статистика
            </h2>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-gray-800/50 rounded-lg p-2">
                <div className="text-gray-400">Пользователей</div>
                <div className="text-lg font-bold text-white">{stats.total_users}</div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-2">
                <div className="text-gray-400">Шаблонов</div>
                <div className="text-lg font-bold text-white">
                  {stats.active_templates}/{stats.total_templates}
                </div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-2">
                <div className="text-gray-400">Карт у юзеров</div>
                <div className="text-lg font-bold text-white">{stats.total_user_cards}</div>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-2">
                <div className="text-gray-400">По редкостям</div>
                <div className="text-xs text-gray-300">
                  {Object.entries(stats.cards_by_rarity).map(([r, c]) => (
                    <span key={r} className={cn('mr-1', RARITY_COLORS[r])}>
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Genres List */}
      <div className="space-y-3">
        <h2 className="font-semibold text-white flex items-center gap-2">
          <Layers className="w-4 h-4" />
          Пул карт по жанрам
        </h2>

        {GENRES.map((genre) => {
          const genreData = poolStatus?.genres[genre];
          const scheduleData = schedule?.genres[genre];
          const isExpanded = expandedGenre === genre;

          return (
            <Card key={genre} className="bg-gray-800/50 border-gray-700/50">
              {/* Genre Header */}
              <button
                onClick={() => setExpandedGenre(isExpanded ? null : genre)}
                className="w-full p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="text-2xl">
                    {genre === 'magic' && '🔮'}
                    {genre === 'fantasy' && '🐉'}
                    {genre === 'scifi' && '🚀'}
                    {genre === 'cyberpunk' && '🤖'}
                    {genre === 'anime' && '⚔️'}
                  </div>
                  <div className="text-left">
                    <div className="font-medium text-white">{GENRE_LABELS[genre]}</div>
                    <div className="text-xs text-gray-400">
                      <Users className="w-3 h-3 inline mr-1" />
                      {genreData?.users_count || 0} юзеров •{' '}
                      <span className="text-green-400">{genreData?.active_templates || 0}</span>/
                      {genreData?.total_templates || 0} карт
                    </div>
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </button>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="px-3 pb-3 space-y-3 border-t border-gray-700/50 pt-3">
                  {/* Generation Schedule */}
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-gray-300 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      Статус генерации
                    </h4>
                    <div className="grid grid-cols-1 gap-1.5 text-xs">
                      {RARITIES.map((rarity) => {
                        const raritySchedule = scheduleData?.schedule[rarity];
                        const isNeedsMore = raritySchedule?.status === 'needs_generation';
                        const isAlwaysNew = raritySchedule?.status === 'always_new';

                        return (
                          <div
                            key={rarity}
                            className={cn(
                              'flex items-center justify-between p-2 rounded',
                              isNeedsMore ? 'bg-red-900/20 border border-red-500/30' : 'bg-gray-700/30'
                            )}
                          >
                            <div className="flex items-center gap-2">
                              <span className={RARITY_COLORS[rarity]}>{RARITY_LABELS[rarity]}</span>
                              {isNeedsMore && <AlertCircle className="w-3.5 h-3.5 text-red-400" />}
                              {!isNeedsMore && !isAlwaysNew && <CheckCircle className="w-3.5 h-3.5 text-green-400" />}
                              {isAlwaysNew && <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-gray-400">{raritySchedule?.message}</span>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 px-2 text-xs"
                                onClick={() => handleGenerate(genre, rarity)}
                                disabled={generatingFor?.genre === genre && generatingFor?.rarity === rarity}
                              >
                                {generatingFor?.genre === genre && generatingFor?.rarity === rarity ? (
                                  <RefreshCw className="w-3 h-3 animate-spin" />
                                ) : (
                                  <Plus className="w-3 h-3" />
                                )}
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Templates List */}
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-gray-300 flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5" />
                      Шаблоны ({templatesData?.total || 0})
                    </h4>

                    {templatesLoading ? (
                      <div className="text-center py-4">
                        <RefreshCw className="w-5 h-5 text-gray-400 animate-spin mx-auto" />
                      </div>
                    ) : (
                      <div className="max-h-60 overflow-y-auto space-y-1">
                        {templatesData?.templates.map((template: CardTemplate) => (
                          <div
                            key={template.id}
                            className={cn(
                              'flex items-center gap-2 p-2 rounded text-xs',
                              template.is_active ? 'bg-gray-700/30' : 'bg-red-900/10 border border-red-500/20'
                            )}
                          >
                            {/* Image */}
                            <div className="w-8 h-8 rounded bg-gray-700 flex items-center justify-center shrink-0">
                              {template.image_url ? (
                                <img
                                  src={template.image_url}
                                  alt={template.name}
                                  className="w-full h-full object-cover rounded"
                                />
                              ) : (
                                <span>{template.emoji}</span>
                              )}
                            </div>

                            {/* Info */}
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-white truncate">{template.name}</div>
                              <div className="text-gray-500 truncate">{template.description}</div>
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-1 shrink-0">
                              {!template.image_url && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-6 w-6 p-0"
                                  onClick={() => generateImageMutation.mutate(template.id)}
                                  disabled={generateImageMutation.isPending}
                                  title="Генерировать изображение"
                                >
                                  <Image className="w-3.5 h-3.5" />
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 w-6 p-0"
                                onClick={() => toggleMutation.mutate(template.id)}
                                disabled={toggleMutation.isPending}
                                title={template.is_active ? 'Отключить' : 'Включить'}
                              >
                                {template.is_active ? (
                                  <ToggleRight className="w-4 h-4 text-green-400" />
                                ) : (
                                  <ToggleLeft className="w-4 h-4 text-red-400" />
                                )}
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
