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
  BarChart3,
  Menu,
  X,
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

type AdminSection = 'stats' | 'cards';

const MENU_ITEMS: { id: AdminSection; label: string; icon: typeof BarChart3 }[] = [
  { id: 'stats', label: 'Статистика', icon: BarChart3 },
  { id: 'cards', label: 'Пул карт', icon: Layers },
];

export default function AdminPage() {
  const queryClient = useQueryClient();
  const [activeSection, setActiveSection] = useState<AdminSection>('stats');
  const [sidebarOpen, setSidebarOpen] = useState(false);
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

  const handleMenuClick = (section: AdminSection) => {
    setActiveSection(section);
    setSidebarOpen(false);
  };

  if (poolLoading || scheduleLoading) {
    return (
      <div className="p-4 flex items-center justify-center min-h-screen">
        <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Mobile Header */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-purple-500" />
          <span className="font-bold text-white">Админ</span>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 text-gray-400 hover:text-white"
        >
          {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={cn(
            'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-gray-800/95 backdrop-blur-sm border-r border-gray-700 transform transition-transform lg:transform-none',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          )}
        >
          {/* Sidebar Header */}
          <div className="hidden lg:flex items-center gap-3 p-4 border-b border-gray-700">
            <Shield className="w-8 h-8 text-purple-500" />
            <div>
              <h1 className="font-bold text-white">Админ-панель</h1>
              <p className="text-xs text-gray-400">MoodSprint</p>
            </div>
          </div>

          {/* Menu */}
          <nav className="p-4 space-y-1 mt-14 lg:mt-0">
            {MENU_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleMenuClick(item.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                    isActive
                      ? 'bg-purple-500/20 text-purple-400'
                      : 'text-gray-400 hover:bg-gray-700/50 hover:text-white'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Overlay for mobile */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main Content */}
        <main className="flex-1 p-4 pb-24 lg:p-6 overflow-auto">
          {/* Stats Section */}
          {activeSection === 'stats' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <BarChart3 className="w-6 h-6" />
                Общая статистика
              </h2>

              {stats && (
                <>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <Card className="bg-gray-800/50 border-gray-700/50">
                      <div className="p-4 text-center">
                        <Users className="w-8 h-8 mx-auto text-blue-400 mb-2" />
                        <div className="text-2xl font-bold text-white">{stats.total_users}</div>
                        <div className="text-sm text-gray-400">Пользователей</div>
                      </div>
                    </Card>
                    <Card className="bg-gray-800/50 border-gray-700/50">
                      <div className="p-4 text-center">
                        <Layers className="w-8 h-8 mx-auto text-purple-400 mb-2" />
                        <div className="text-2xl font-bold text-white">
                          {stats.active_templates}/{stats.total_templates}
                        </div>
                        <div className="text-sm text-gray-400">Шаблонов</div>
                      </div>
                    </Card>
                    <Card className="bg-gray-800/50 border-gray-700/50">
                      <div className="p-4 text-center">
                        <Sparkles className="w-8 h-8 mx-auto text-amber-400 mb-2" />
                        <div className="text-2xl font-bold text-white">{stats.total_user_cards}</div>
                        <div className="text-sm text-gray-400">Карт у юзеров</div>
                      </div>
                    </Card>
                    <Card className="bg-gray-800/50 border-gray-700/50">
                      <div className="p-4">
                        <div className="text-sm text-gray-400 mb-2">По редкостям</div>
                        <div className="space-y-1">
                          {Object.entries(stats.cards_by_rarity).map(([r, c]) => (
                            <div key={r} className="flex justify-between text-sm">
                              <span className={RARITY_COLORS[r]}>{RARITY_LABELS[r]}</span>
                              <span className="text-white">{c}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </Card>
                  </div>

                  <Card className="bg-gray-800/50 border-gray-700/50">
                    <div className="p-4">
                      <h3 className="font-semibold text-white mb-3">Пользователи по жанрам</h3>
                      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
                        {Object.entries(stats.users_by_genre).map(([genre, count]) => (
                          <div key={genre} className="bg-gray-700/30 rounded-lg p-3 text-center">
                            <div className="text-2xl mb-1">
                              {genre === 'magic' && '🔮'}
                              {genre === 'fantasy' && '🐉'}
                              {genre === 'scifi' && '🚀'}
                              {genre === 'cyberpunk' && '🤖'}
                              {genre === 'anime' && '⚔️'}
                            </div>
                            <div className="text-lg font-bold text-white">{count}</div>
                            <div className="text-xs text-gray-400">{GENRE_LABELS[genre]}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </Card>
                </>
              )}
            </div>
          )}

          {/* Cards Section */}
          {activeSection === 'cards' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Layers className="w-6 h-6" />
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
          )}
        </main>
      </div>
    </div>
  );
}
