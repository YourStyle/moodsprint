'use client';

import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
  Plus,
} from 'lucide-react';
import { Card, Button, Progress, ScrollBackdrop, Modal } from '@/components/ui';
import { LoreSheet, DialogueSheet } from '@/components/campaign';
import { GenreSelector } from '@/components/GenreSelector';
import { campaignService, onboardingService, gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';
import { useLanguage } from '@/lib/i18n';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { cn } from '@/lib/utils';
import type { CampaignChapter, CampaignLevel } from '@/services/campaign';

export default function CampaignPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();
  const { t } = useLanguage();

  const [selectedChapter, setSelectedChapter] = useState<CampaignChapter | null>(null);
  const [showLevelSelect, setShowLevelSelect] = useState(false);
  const [showIntro, setShowIntro] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState<CampaignLevel | null>(null);
  const [showDialogue, setShowDialogue] = useState(false);
  const [showEnergyInfo, setShowEnergyInfo] = useState(false);
  const [showGenreWarning, setShowGenreWarning] = useState(false);
  const [pendingGenre, setPendingGenre] = useState<string | null>(null);

  useEffect(() => {
    // Only show back button when in sub-views (level select or dialogue),
    // not at root chapter list (since campaign is now a tab page)
    if (showLevelSelect || showDialogue) {
      showBackButton(() => {
        if (showDialogue) {
          setShowDialogue(false);
          setSelectedLevel(null);
        } else if (showLevelSelect) {
          setShowLevelSelect(false);
          setSelectedChapter(null);
        }
      });
      return () => hideBackButton();
    } else {
      hideBackButton();
    }
  }, [showLevelSelect, showDialogue]);

  // Get campaign overview
  const { data: campaignData, isLoading } = useQuery({
    queryKey: ['campaign', 'overview'],
    queryFn: () => campaignService.getCampaignOverview(),
    enabled: !!user,
  });

  // Get profile for genre selector
  const { data: profileData } = useQuery({
    queryKey: ['onboarding', 'profile'],
    queryFn: () => onboardingService.getProfile(),
    enabled: !!user,
  });
  const profile = profileData?.data?.profile;

  // Get chapter details when selected
  const { data: chapterData, isLoading: chapterLoading } = useQuery({
    queryKey: ['campaign', 'chapter', selectedChapter?.number],
    queryFn: () => campaignService.getChapterDetails(selectedChapter!.number),
    enabled: !!selectedChapter && showLevelSelect,
  });

  const progress = campaignData?.data?.progress;
  const chapters = campaignData?.data?.chapters || [];
  const energy = campaignData?.data?.energy ?? 3;
  const maxEnergy = campaignData?.data?.max_energy ?? 5;

  const handleChapterClick = (chapter: CampaignChapter) => {
    if (!chapter.is_unlocked) {
      hapticFeedback('error');
      return;
    }
    hapticFeedback('light');
    setSelectedChapter(chapter);
    setShowLevelSelect(true);

    // Show intro only if chapter has one, not completed, and never shown before
    const introShownKey = `chapter_intro_shown_${chapter.id}`;
    const introAlreadyShown = localStorage.getItem(introShownKey);
    if (chapter.story_intro && !chapter.is_completed && !introAlreadyShown) {
      setShowIntro(true);
      localStorage.setItem(introShownKey, 'true');
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
    // Energy check: chapter 1 is free, rest costs 1 energy
    const chapterNum = selectedChapter?.number || 1;
    if (chapterNum > 1 && energy <= 0) {
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
    if (selectedLevel?.monster) {
      return {
        name: selectedLevel.monster.name,
        emoji: selectedLevel.monster.emoji,
        imageUrl: selectedLevel.monster.sprite_url,
      };
    }
    return {
      name: selectedLevel?.is_boss ? t('bossLevel') : t('selectMonster'),
      emoji: selectedLevel?.is_boss ? '👹' : '👾',
      imageUrl: undefined,
    };
  };

  // Prefetch chapter data on hover
  const handleChapterHover = (chapter: CampaignChapter) => {
    if (chapter.is_unlocked) {
      queryClient.prefetchQuery({
        queryKey: ['campaign', 'chapter', chapter.number],
        queryFn: () => campaignService.getChapterDetails(chapter.number),
        staleTime: 1000 * 60 * 5, // 5 minutes
      });
    }
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

  const handleBeforeGenreSwitch = (genre: string): boolean => {
    const warningShown = localStorage.getItem('genre_switch_warning_shown');
    if (!warningShown) {
      setPendingGenre(genre);
      setShowGenreWarning(true);
      return false; // Cancel — modal will handle the switch
    }
    return true; // Proceed immediately
  };

  const handleGenreWarningConfirm = () => {
    localStorage.setItem('genre_switch_warning_shown', 'true');
    setShowGenreWarning(false);
    if (pendingGenre) {
      gamificationService.setGenre(pendingGenre as any).then(() => {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['onboarding', 'profile'] });
        queryClient.invalidateQueries({ queryKey: ['campaign'] });
        queryClient.invalidateQueries({ queryKey: ['cards'] });
        queryClient.invalidateQueries({ queryKey: ['card-templates'] });
      });
      setPendingGenre(null);
    }
  };

  if (!showLevelSelect) {
    return (
      <div className="p-4 pb-4">
        {/* Header */}
        <div className="mb-4">
          <div className="flex items-center gap-3">
            <Map className="w-8 h-8 text-purple-500" />
            <div className="flex-1">
              <h1 className="text-xl font-bold text-white">{t('campaign')}</h1>
              <p className="text-sm text-gray-400">{t('campaignSubtitle')}</p>
            </div>
          </div>

          {progress && (
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <GenreSelector
                currentGenre={profile?.favorite_genre}
                onBeforeSwitch={handleBeforeGenreSwitch}
              />
              <div className="flex items-center gap-1.5 bg-amber-500/20 px-3 py-1.5 rounded-full">
                <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                <span className="text-amber-400 font-medium">{progress.total_stars_earned} {t('stars')}</span>
              </div>
              <div className="flex items-center gap-1">
                <div className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full',
                  energy > 0 ? 'bg-cyan-500/20' : 'bg-red-500/20'
                )}>
                  <span className="text-base">⚡</span>
                  <span className={cn(
                    'font-medium',
                    energy > 0 ? 'text-cyan-400' : 'text-red-400'
                  )}>
                    {energy}/{maxEnergy}
                  </span>
                </div>
                <button
                  onClick={() => setShowEnergyInfo(true)}
                  className="w-6 h-6 rounded-full bg-cyan-500/20 flex items-center justify-center hover:bg-cyan-500/30 transition-colors"
                >
                  <Plus className="w-3 h-3 text-cyan-400" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Arena Banner */}
        <Card
          className="bg-gradient-to-r from-red-900/30 to-purple-900/30 border-red-500/20 mb-4 cursor-pointer"
          onClick={() => router.push('/arena')}
        >
          <div className="p-3 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
              <Swords className="w-5 h-5 text-red-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-bold text-white text-sm">{t('arena')}</h3>
              <p className="text-xs text-gray-400">{t('arenaDesc')}</p>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400 shrink-0" />
          </div>
        </Card>

        {/* Chapters List */}
        {isLoading ? (
            <div className="text-center text-gray-400 py-8">{t('loading')}</div>
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
                  onMouseEnter={() => handleChapterHover(chapter)}
                  onTouchStart={() => handleChapterHover(chapter)}
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
                            <h3 className="font-bold text-white">{t('chapter')} {chapter.number}</h3>
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
                          {t('levelsCount')}: {chapter.levels_completed}/{chapter.total_levels}
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
                      <span>{t('rewardLabel')}: {chapter.guaranteed_card_rarity} {t('cardLabel')} + {chapter.xp_reward} XP</span>
                      <span className="flex items-center gap-0.5 text-amber-400">
                        <Sparkles className="w-3 h-3" />
                        90✨
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

        {/* Energy Info Modal */}
        <Modal isOpen={showEnergyInfo} onClose={() => setShowEnergyInfo(false)} title={t('energyInfoTitle')}>
          <div className="space-y-3">
            {[
              { emoji: '✅', label: t('energySourceTask'), value: '+1 ⚡' },
              { emoji: '🎯', label: t('energySourceFocus'), value: '+1 ⚡' },
              { emoji: '⬆️', label: t('energySourceLevelUp'), value: '⚡ +max' },
            ].map((source) => (
              <div key={source.label} className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-xl">
                <span className="text-xl">{source.emoji}</span>
                <span className="flex-1 text-sm text-gray-300">{source.label}</span>
                <span className="text-sm font-medium text-cyan-400">{source.value}</span>
              </div>
            ))}
          </div>
        </Modal>

        {/* Genre Switch Warning Modal */}
        <Modal isOpen={showGenreWarning} onClose={() => { setShowGenreWarning(false); setPendingGenre(null); }} title={t('genreSwitchTitle')}>
          <p className="text-sm text-gray-400 mb-4">{t('genreSwitchWarning')}</p>
          <div className="flex gap-3">
            <Button
              className="flex-1 bg-gray-700 hover:bg-gray-600 text-white"
              onClick={() => { setShowGenreWarning(false); setPendingGenre(null); }}
            >
              {t('cancel')}
            </Button>
            <Button
              className="flex-1 bg-purple-600 hover:bg-purple-500 text-white"
              onClick={handleGenreWarningConfirm}
            >
              {t('confirm')}
            </Button>
          </div>
        </Modal>
      </div>
    );
  }

  // Level selection view
  return (
    <div className="p-4 pt-6 pb-4">
      <ScrollBackdrop />
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
                    {t('chapter')} {selectedChapter.number}: {selectedChapter.name}
                  </h2>
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <div className="flex items-center gap-1 text-amber-400">
                      <Star className="w-3.5 h-3.5 fill-current" />
                      {selectedChapter.stars_earned}/{selectedChapter.max_stars}
                    </div>
                    <span className="text-gray-600">•</span>
                    <span>{selectedChapter.levels_completed}/{selectedChapter.total_levels} {t('levelsShort')}</span>
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

        {/* Levels — Vertical Progression Path */}
        {chapterLoading ? (
          <div className="text-center text-gray-400 py-8">{t('loading')}</div>
        ) : (
          <div className="mt-4">
            {chapterData?.data?.levels?.map((level, index) => {
              const levels = chapterData.data!.levels!;
              const isLast = index === levels.length - 1;
              const isCompleted = level.is_completed;
              const isUnlocked = level.is_unlocked;
              const isBoss = level.is_boss;

              // Node colors
              const nodeColor = isCompleted
                ? 'bg-green-500 border-green-400'
                : isUnlocked
                  ? 'bg-purple-500/20 border-purple-500 ring-2 ring-purple-500/50'
                  : 'bg-gray-700 border-gray-600';
              const bossNodeColor = isCompleted
                ? 'bg-green-500 border-green-400 shadow-[0_0_15px_rgba(34,197,94,0.4)]'
                : isUnlocked
                  ? 'bg-red-500/20 border-red-500 ring-2 ring-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                  : 'bg-gray-700 border-gray-600';

              // Connector color
              const connectorColor = isCompleted ? 'from-green-500 to-green-500/30' : 'from-gray-600 to-gray-700';

              return (
                <div key={level.id} className="flex items-start gap-3">
                  {/* Node column: circle + connector line */}
                  <div className="flex flex-col items-center shrink-0">
                    {/* Circle node */}
                    <div
                      className={cn(
                        'rounded-full border-2 flex items-center justify-center transition-all',
                        isBoss ? 'w-12 h-12' : 'w-10 h-10',
                        isBoss ? bossNodeColor : nodeColor,
                        isUnlocked && !isCompleted && 'animate-pulse',
                        !isUnlocked && 'opacity-50'
                      )}
                    >
                      {isBoss ? (
                        <Crown className={cn('w-5 h-5', isCompleted ? 'text-white' : isUnlocked ? 'text-red-400' : 'text-gray-500')} />
                      ) : isCompleted ? (
                        <Check className="w-5 h-5 text-white" />
                      ) : isUnlocked ? (
                        <span className="text-sm font-bold text-white">{level.number}</span>
                      ) : (
                        <Lock className="w-4 h-4 text-gray-500" />
                      )}
                    </div>
                    {/* Connector line */}
                    {!isLast && (
                      <div className={cn(
                        'w-0.5 h-8 bg-gradient-to-b',
                        connectorColor
                      )} />
                    )}
                  </div>

                  {/* Info card */}
                  <div
                    className={cn(
                      'flex-1 rounded-xl overflow-hidden transition-all border mb-2',
                      isBoss
                        ? 'bg-gradient-to-r from-red-900/40 to-orange-900/40 border-red-500/40'
                        : isCompleted
                          ? 'bg-gray-800/40 border-green-500/30'
                          : 'bg-gray-800/60 border-gray-700/40',
                      !isUnlocked && 'opacity-50 grayscale',
                      isUnlocked && 'cursor-pointer'
                    )}
                    onClick={() => handleLevelStart(level)}
                  >
                    <div className="px-3 py-2.5 flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium text-white text-sm truncate">
                            {level.title || (isBoss ? t('bossLevel').toUpperCase() : `${t('levelNumber')} ${level.number}`)}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                          <span>+{level.xp_reward} XP</span>
                          <span className="flex items-center gap-0.5 text-purple-400">
                            <Sparkles className="w-3 h-3" />
                            {isBoss ? '65' : '15'}
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

                      {/* Play icon for unlocked levels */}
                      {isUnlocked && !isCompleted && (
                        <Play className="w-4 h-4 text-purple-400 shrink-0" />
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Chapter Rewards */}
        {chapterData?.data?.rewards && chapterData.data.rewards.length > 0 && (
          <Card className="bg-gradient-to-br from-amber-900/20 to-yellow-900/20 border-amber-500/30 mt-4">
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <Gift className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-white">{t('chapterRewards')}</h3>
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
            title={`${t('chapter')} ${selectedChapter.number}`}
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
            monsterImageUrl={getMonsterForLevel().imageUrl}
            dialogue={selectedLevel.dialogue_before.map(d => ({
              speaker: d.speaker,
              text: d.text,
              emoji: d.emoji,
            }))}
            title={selectedLevel.title || `${t('levelNumber')} ${selectedLevel.number}`}
            showSkipButton={selectedLevel.is_completed || selectedLevel.attempts > 0}
          />
        )}
    </div>
  );
}
