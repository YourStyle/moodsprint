'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Map,
  Star,
  Lock,
  Check,
  ChevronRight,
  Swords,
  Crown,
  Sparkles,
  Gift,
  Play,
} from 'lucide-react';
import { Card, Button, Progress } from '@/components/ui';
import { LoreSheet, DialogueSheet } from '@/components/campaign';
import { campaignService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { CampaignChapter, CampaignLevel } from '@/services/campaign';

export default function CampaignPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  const [selectedChapter, setSelectedChapter] = useState<CampaignChapter | null>(null);
  const [showLevelSelect, setShowLevelSelect] = useState(false);
  const [showIntro, setShowIntro] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState<CampaignLevel | null>(null);
  const [showDialogue, setShowDialogue] = useState(false);

  useEffect(() => {
    showBackButton(() => {
      if (showDialogue) {
        setShowDialogue(false);
        setSelectedLevel(null);
      } else if (showLevelSelect) {
        setShowLevelSelect(false);
        setSelectedChapter(null);
      } else {
        router.back();
      }
    });
    return () => hideBackButton();
  }, [router, showLevelSelect, showDialogue]);

  // Get campaign overview
  const { data: campaignData, isLoading } = useQuery({
    queryKey: ['campaign', 'overview'],
    queryFn: () => campaignService.getCampaignOverview(),
    enabled: !!user,
  });

  // Get chapter details when selected
  const { data: chapterData, isLoading: chapterLoading } = useQuery({
    queryKey: ['campaign', 'chapter', selectedChapter?.number],
    queryFn: () => campaignService.getChapterDetails(selectedChapter!.number),
    enabled: !!selectedChapter && showLevelSelect,
  });

  const progress = campaignData?.data?.progress;
  const chapters = campaignData?.data?.chapters || [];

  const handleChapterClick = (chapter: CampaignChapter) => {
    if (!chapter.is_unlocked) {
      hapticFeedback('error');
      return;
    }
    hapticFeedback('light');
    setSelectedChapter(chapter);
    setShowLevelSelect(true);

    // Show intro only if chapter has one, not completed, and never visited (0 levels completed)
    if (chapter.story_intro && !chapter.is_completed && chapter.levels_completed === 0) {
      setShowIntro(true);
    }
  };

  const handleIntroClose = () => {
    setShowIntro(false);
  };

  const handleLevelStart = (level: CampaignLevel) => {
    if (!level.is_unlocked) {
      hapticFeedback('error');
      return;
    }
    hapticFeedback('medium');
    setSelectedLevel(level);

    // Show dialogue if level has one
    if (level.dialogue_before && level.dialogue_before.length > 0) {
      setShowDialogue(true);
    } else {
      // Navigate directly to battle
      router.push(`/arena?campaign_level=${level.id}`);
    }
  };

  const handleDialogueClose = () => {
    setShowDialogue(false);
    setSelectedLevel(null);
  };

  const handleDialogueContinue = () => {
    if (selectedLevel) {
      setShowDialogue(false);
      router.push(`/arena?campaign_level=${selectedLevel.id}`);
    }
  };

  // Get monster info for the selected level
  const getMonsterForLevel = () => {
    // This would need monster data from the level
    // For now return placeholder - we'll get real data from chapterData
    return {
      name: selectedLevel?.is_boss ? 'Босс' : 'Монстр',
      emoji: selectedLevel?.is_boss ? '👹' : '👾',
    };
  };

  const getGenreGradient = (genre: string) => {
    const gradients: Record<string, string> = {
      fantasy: 'from-amber-900/40 to-orange-900/40',
      magic: 'from-purple-900/40 to-pink-900/40',
      cyberpunk: 'from-cyan-900/40 to-blue-900/40',
      scifi: 'from-indigo-900/40 to-violet-900/40',
      anime: 'from-rose-900/40 to-red-900/40',
    };
    return gradients[genre] || 'from-gray-800/40 to-gray-900/40';
  };

  const getGenreBorder = (genre: string) => {
    const borders: Record<string, string> = {
      fantasy: 'border-amber-500/30',
      magic: 'border-purple-500/30',
      cyberpunk: 'border-cyan-500/30',
      scifi: 'border-indigo-500/30',
      anime: 'border-rose-500/30',
    };
    return borders[genre] || 'border-gray-700/50';
  };

  if (!showLevelSelect) {
    return (
      <div className="p-4 pb-4">
        {/* Header */}
        <div className="text-center mb-4">
          <Map className="w-10 h-10 text-purple-500 mx-auto mb-2" />
          <h1 className="text-2xl font-bold text-white">Кампания</h1>
          <p className="text-sm text-gray-400">Проходи главы и получай награды</p>
          {progress && (
            <div className="flex items-center justify-center gap-1.5 bg-amber-500/20 px-3 py-1.5 rounded-full mt-3 w-fit mx-auto">
              <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
              <span className="text-amber-400 font-medium">{progress.total_stars_earned} звёзд</span>
            </div>
          )}
        </div>

        {/* Progress Overview */}
        {progress && (
          <Card className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 border-purple-500/30 mb-4">
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="text-sm text-gray-400">Прогресс</div>
                    <div className="text-lg font-bold text-white">
                      Глава {progress.current_chapter}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="text-center">
                      <div className="text-gray-400">Боссов</div>
                      <div className="text-purple-400 font-bold">{progress.bosses_defeated}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-gray-400">Звёзд</div>
                      <div className="text-amber-400 font-bold">{progress.total_stars_earned}</div>
                    </div>
                  </div>
                </div>
            </div>
          </Card>
        )}

        {/* Chapters List */}
        {isLoading ? (
            <div className="text-center text-gray-400 py-8">Загрузка...</div>
          ) : (
            <div className="space-y-3">
              {chapters.map((chapter) => (
                <Card
                  key={chapter.id}
                  className={cn(
                    'overflow-hidden transition-all cursor-pointer',
                    `bg-gradient-to-br ${getGenreGradient(chapter.genre)}`,
                    getGenreBorder(chapter.genre),
                    !chapter.is_unlocked && 'opacity-60 grayscale'
                  )}
                  onClick={() => handleChapterClick(chapter)}
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                          style={{ backgroundColor: chapter.background_color + '40' }}
                        >
                          {chapter.emoji}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-white">Глава {chapter.number}</h3>
                            {chapter.is_completed && (
                              <Check className="w-4 h-4 text-green-400" />
                            )}
                            {!chapter.is_unlocked && (
                              <Lock className="w-4 h-4 text-gray-500" />
                            )}
                          </div>
                          <div className="text-sm text-gray-300">{chapter.name}</div>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>

                    {chapter.description && (
                      <p className="text-sm text-gray-400 mb-3 line-clamp-2">
                        {chapter.description}
                      </p>
                    )}

                    {/* Progress */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">
                          Уровней: {chapter.levels_completed}/{chapter.total_levels}
                        </span>
                        <div className="flex items-center gap-1 text-amber-400">
                          <Star className="w-3.5 h-3.5 fill-current" />
                          <span>{chapter.stars_earned}/{chapter.max_stars}</span>
                        </div>
                      </div>
                      <Progress
                        value={(chapter.levels_completed / chapter.total_levels) * 100}
                        className="h-2 bg-gray-700/50"
                      />
                    </div>

                    {/* Rewards hint */}
                    <div className="mt-3 pt-3 border-t border-white/10 flex items-center gap-2 text-xs text-gray-400">
                      <Gift className="w-3.5 h-3.5" />
                      <span>Награда: {chapter.guaranteed_card_rarity} карта + {chapter.xp_reward} XP</span>
                      <span className="flex items-center gap-0.5 text-amber-400">
                        <Sparkles className="w-3 h-3" />
                        до 90✨
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
      </div>
    );
  }

  // Level selection view
  return (
    <div className="p-4 pt-6 pb-4">
      {/* Chapter Header */}
      {selectedChapter && (
          <Card
            className={cn(
              'overflow-hidden',
              `bg-gradient-to-br ${getGenreGradient(selectedChapter.genre)}`,
              getGenreBorder(selectedChapter.genre)
            )}
          >
            <div className="p-4">
              <div className="flex items-center gap-3 mb-2">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0"
                  style={{ backgroundColor: selectedChapter.background_color + '40' }}
                >
                  {selectedChapter.emoji}
                </div>
                <div className="min-w-0">
                  <h2 className="text-base font-bold text-white truncate">
                    Глава {selectedChapter.number}: {selectedChapter.name}
                  </h2>
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <div className="flex items-center gap-1 text-amber-400">
                      <Star className="w-3.5 h-3.5 fill-current" />
                      {selectedChapter.stars_earned}/{selectedChapter.max_stars}
                    </div>
                    <span className="text-gray-600">•</span>
                    <span>{selectedChapter.levels_completed}/{selectedChapter.total_levels} уровней</span>
                  </div>
                </div>
              </div>

              {chapterData?.data?.story_intro && (
                <p className="text-sm text-gray-400 mt-2 line-clamp-2">
                  {chapterData.data.story_intro}
                </p>
              )}
            </div>
          </Card>
        )}

        {/* Levels List */}
        {chapterLoading ? (
          <div className="text-center text-gray-400 py-8">Загрузка...</div>
        ) : (
          <div className="space-y-2 mt-4">
            {chapterData?.data?.levels?.map((level, index) => (
              <div
                key={level.id}
                className={cn(
                  'rounded-xl overflow-hidden transition-all cursor-pointer border',
                  level.is_boss
                    ? 'bg-gradient-to-r from-red-900/40 to-orange-900/40 border-red-500/40'
                    : 'bg-gray-800/60 border-gray-700/40',
                  !level.is_unlocked && 'opacity-50 grayscale',
                  level.is_completed && 'ring-1 ring-green-500/30'
                )}
                onClick={() => handleLevelStart(level)}
              >
                <div className="px-3 py-2.5 flex items-center gap-3">
                  {/* Level number */}
                  <div className={cn(
                    'w-10 h-10 rounded-lg flex items-center justify-center shrink-0',
                    level.is_boss
                      ? 'bg-red-600/40'
                      : 'bg-gray-700/60'
                  )}>
                    {level.is_boss ? (
                      <Crown className="w-5 h-5 text-red-400" />
                    ) : level.is_unlocked ? (
                      <span className="text-base font-bold text-white">{level.number}</span>
                    ) : (
                      <Lock className="w-4 h-4 text-gray-500" />
                    )}
                  </div>

                  {/* Level info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-white text-sm truncate">
                        {level.title || (level.is_boss ? 'БОСС' : `Уровень ${level.number}`)}
                      </h3>
                      {level.is_completed && (
                        <Check className="w-3.5 h-3.5 text-green-400 shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                      <span>+{level.xp_reward} XP</span>
                      <span className="flex items-center gap-0.5 text-purple-400">
                        <Sparkles className="w-3 h-3" />
                        {level.is_boss ? '65' : '15'}
                      </span>
                    </div>
                  </div>

                  {/* Stars */}
                  <div className="flex items-center gap-0.5 shrink-0">
                    {[1, 2, 3].map((star) => (
                      <Star
                        key={star}
                        className={cn(
                          'w-4 h-4',
                          level.stars_earned >= star
                            ? 'text-amber-400 fill-amber-400'
                            : 'text-gray-600'
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Chapter Rewards */}
        {chapterData?.data?.rewards && chapterData.data.rewards.length > 0 && (
          <Card className="bg-gradient-to-br from-amber-900/20 to-yellow-900/20 border-amber-500/30 mt-4">
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Gift className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-white">Награды за прохождение главы</h3>
              </div>
              <div className="space-y-2">
                {chapterData.data.rewards.map((reward) => (
                  <div
                    key={reward.id}
                    className="flex items-center gap-3 p-2 bg-black/20 rounded-lg"
                  >
                    <span className="text-xl">{reward.emoji}</span>
                    <div>
                      <div className="text-sm font-medium text-white">
                        {reward.reward_type === 'sparks' && reward.reward_data?.amount
                          ? `${reward.reward_data.amount} Sparks`
                          : reward.name}
                      </div>
                      {reward.description && (
                        <div className="text-xs text-gray-400">{reward.description}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}

        {/* Intro Sheet */}
        {selectedChapter && (
          <LoreSheet
            isOpen={showIntro}
            onClose={handleIntroClose}
            type="chapter_complete"
            title={`Глава ${selectedChapter.number}`}
            subtitle={selectedChapter.name}
            emoji={selectedChapter.emoji}
            text={chapterData?.data?.story_intro || selectedChapter.story_intro || ''}
          />
        )}

        {/* Dialogue Sheet */}
        {selectedLevel && selectedLevel.dialogue_before && (
          <DialogueSheet
            isOpen={showDialogue}
            onClose={handleDialogueClose}
            onContinue={handleDialogueContinue}
            monsterName={getMonsterForLevel().name}
            monsterEmoji={getMonsterForLevel().emoji}
            dialogue={selectedLevel.dialogue_before.map(d => ({
              speaker: d.speaker,
              text: d.text,
              emoji: d.emoji,
            }))}
            title={selectedLevel.title || `Уровень ${selectedLevel.number}`}
            showSkipButton={selectedLevel.is_completed || selectedLevel.attempts > 0}
          />
        )}
    </div>
  );
}
