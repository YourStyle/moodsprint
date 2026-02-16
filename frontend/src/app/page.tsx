'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Plus, Sparkles, Play, Pause, Square, ArrowUp, X, Smile, Timer, CheckCircle2, Search, ChevronDown, ChevronRight, ChevronLeft, List, LayoutGrid } from 'lucide-react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { Button, Card, Modal, ScrollBackdrop } from '@/components/ui';
import { MoodSelector } from '@/components/mood';
import { TaskForm } from '@/components/tasks';
import { DailyBonus, LevelUpModal, EnergyLimitModal, type LevelRewardItem } from '@/components/gamification';
import { StreakIndicator } from '@/components/gamification/StreakIndicator';
import { StreakMilestoneModal } from '@/components/gamification/StreakMilestoneModal';
import { CardEarnedModal, CardTutorial, shouldShowCardTutorial, type EarnedCard } from '@/components/cards';
import { SpotlightOnboarding, type OnboardingStep } from '@/components/SpotlightOnboarding';
import { LandingPage } from '@/components/LandingPage';
import { useAppStore } from '@/lib/store';
import { tasksService, moodService, focusService } from '@/services';
import { cardsService } from '@/services/cards';
import { hapticFeedback, isMobileApp } from '@/lib/telegram';
import { MOOD_EMOJIS } from '@/domain/constants';
import { useLanguage, TranslationKey } from '@/lib/i18n';
import type { MoodLevel, EnergyLevel, FocusSession, TaskStatus } from '@/domain/types';

// TODO: Re-enable spotlight onboarding later
const ONBOARDING_STEPS: OnboardingStep[] = [
  // Temporarily disabled
  // {
  //   id: 'create-task',
  //   targetSelector: '[data-onboarding="create-task"]',
  //   title: 'Создание задачи',
  //   description: 'Нажми сюда, чтобы создать новую задачу. AI разобьёт её на маленькие шаги с учётом твоего настроения!',
  //   position: 'bottom',
  // },
  // {
  //   id: 'mood-check',
  //   targetSelector: '[data-onboarding="mood-check"]',
  //   title: 'Проверка настроения',
  //   description: 'Здесь ты можешь отслеживать своё настроение. От него зависит как задачи будут разбиты на шаги.',
  //   position: 'bottom',
  // },
  // {
  //   id: 'nav-deck',
  //   targetSelector: '[data-onboarding="nav-deck"]',
  //   title: 'Твоя колода карт',
  //   description: 'За выполнение задач ты получаешь карты! Собирай колоду, обменивайся с друзьями и сражайся на арене.',
  //   position: 'top',
  // },
];

type FilterStatus = TaskStatus | 'all';

const formatDateForAPI = (date: Date): string => {
  // Use local timezone, not UTC (toISOString converts to UTC which shifts dates)
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const formatDateDisplay = (date: Date, language: 'ru' | 'en', t: (key: TranslationKey) => string): string => {
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

interface WeekCalendarProps {
  selectedDate: Date;
  onDateSelect: (date: Date) => void;
  language: 'ru' | 'en';
  taskCounts?: Record<string, number>;
}

const WEEK_DAYS = {
  ru: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
  en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
};

const MONTH_NAMES = {
  ru: ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
};

function WeekCalendar({ selectedDate, onDateSelect, language, taskCounts = {} }: WeekCalendarProps) {
  const days = WEEK_DAYS[language];
  const months = MONTH_NAMES[language];
  const today = new Date();
  const selectedDateStr = formatDateForAPI(selectedDate);
  const todayStr = formatDateForAPI(today);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showLeftArrow, setShowLeftArrow] = useState(false);
  const [showRightArrow, setShowRightArrow] = useState(true);

  // Generate 38 days: 7 days back + today + 30 days forward
  const allDays = useMemo(() => {
    const result: Date[] = [];
    for (let i = -7; i <= 30; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      result.push(date);
    }
    return result;
  }, []);

  // Find index of selected date in allDays array
  const selectedIndex = useMemo(() => {
    const selectedStr = formatDateForAPI(selectedDate);
    return allDays.findIndex(d => formatDateForAPI(d) === selectedStr);
  }, [allDays, selectedDate]);

  // Default to today's index (7) if selected date not found
  const scrollToIndex = selectedIndex >= 0 ? selectedIndex : 7;

  // Update arrow visibility based on scroll position
  const updateArrowVisibility = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
    setShowLeftArrow(scrollLeft > 10);
    setShowRightArrow(scrollLeft < scrollWidth - clientWidth - 10);
  }, []);

  // Scroll by amount
  const scrollBy = useCallback((direction: 'left' | 'right') => {
    if (!scrollRef.current) return;
    const scrollAmount = 200;
    scrollRef.current.scrollBy({
      left: direction === 'left' ? -scrollAmount : scrollAmount,
      behavior: 'smooth',
    });
  }, []);

  // Initial scroll to selected date (or today if not found)
  useEffect(() => {
    if (scrollRef.current && !scrollRef.current.dataset.scrolled) {
      const container = scrollRef.current.querySelector('.flex.gap-1');
      if (container) {
        const targetElement = container.children[scrollToIndex] as HTMLElement;
        if (targetElement) {
          const scrollLeft = targetElement.offsetLeft - scrollRef.current.clientWidth / 2 + targetElement.clientWidth / 2;
          scrollRef.current.scrollLeft = Math.max(0, scrollLeft);
          scrollRef.current.dataset.scrolled = 'true';
          updateArrowVisibility();
        }
      }
    }
  }, [scrollToIndex, updateArrowVisibility]);

  return (
    <div className="flex items-center gap-1 pt-4">
      {/* Left arrow */}
      <button
        onClick={() => scrollBy('left')}
        disabled={!showLeftArrow}
        className={`flex-shrink-0 w-8 h-16 flex items-center justify-center transition-opacity ${showLeftArrow ? 'opacity-100' : 'opacity-30'}`}
      >
        <ChevronLeft className="w-5 h-5 text-gray-400" />
      </button>

      {/* Scrollable dates */}
      <div
        ref={scrollRef}
        onScroll={updateArrowVisibility}
        className="flex-1 overflow-x-auto pb-1 overflow-y-visible"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        <div className="flex gap-1">
        {allDays.map((date, index) => {
          const dateStr = formatDateForAPI(date);
          const isSelected = dateStr === selectedDateStr;
          const isToday = dateStr === todayStr;
          const taskCount = taskCounts[dateStr] || 0;
          const dayOfWeek = days[date.getDay()];
          const isPast = date < today && !isToday;
          const isNewMonth = date.getDate() === 1 || index === 0;

          return (
            <button
              key={dateStr}
              onClick={() => {
                hapticFeedback('light');
                onDateSelect(date);
              }}
              className={`relative flex flex-col items-center py-2 px-3 rounded-xl transition-all flex-shrink-0 min-w-[52px] mt-2 ${
                isSelected
                  ? 'bg-primary-500/20 border border-primary-500/50'
                  : isToday
                  ? 'bg-dark-600 border border-gray-700'
                  : isPast
                  ? 'opacity-40 hover:opacity-60'
                  : 'opacity-70 hover:opacity-100'
              }`}
            >
              <span className="text-[10px] text-gray-400 mb-0.5">{dayOfWeek}</span>
              <span className={`text-lg font-semibold ${isSelected ? 'text-primary-400' : isToday ? 'text-white' : 'text-gray-400'}`}>
                {date.getDate()}
              </span>
              {isNewMonth && (
                <span className="text-[9px] text-gray-500">{months[date.getMonth()]}</span>
              )}
              {taskCount > 0 && !isSelected && (
                <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-purple-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center">
                  {taskCount > 9 ? '9+' : taskCount}
                </span>
              )}
            </button>
          );
        })}
        </div>
      </div>

      {/* Right arrow */}
      <button
        onClick={() => scrollBy('right')}
        disabled={!showRightArrow}
        className={`flex-shrink-0 w-8 h-16 flex items-center justify-center transition-opacity ${showRightArrow ? 'opacity-100' : 'opacity-30'}`}
      >
        <ChevronRight className="w-5 h-5 text-gray-400" />
      </button>

      <style jsx>{`
        div::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}

// Helper to calculate elapsed seconds
function calculateElapsedSeconds(session: FocusSession): number {
  const startedAt = new Date(session.started_at).getTime();
  const now = Date.now();
  return Math.floor((now - startedAt) / 1000);
}

// Mini timer component for compact cards
function MiniTimer({ session, onPause, onResume, onComplete, onStop }: {
  session: FocusSession;
  onPause: () => void;
  onResume: () => void;
  onComplete: () => void;
  onStop: () => void;
}) {
  const initialElapsed = useMemo(() => {
    if (session.status === 'paused') {
      return session.elapsed_minutes * 60;
    }
    return calculateElapsedSeconds(session);
  }, [session.started_at, session.status, session.elapsed_minutes]);

  const [elapsed, setElapsed] = useState(initialElapsed);
  const isPaused = session.status === 'paused';
  const planned = session.planned_duration_minutes * 60;

  useEffect(() => {
    setElapsed(initialElapsed);
  }, [initialElapsed]);

  useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      setElapsed(calculateElapsedSeconds(session));
    }, 1000);
    return () => clearInterval(interval);
  }, [isPaused, session.started_at]);

  const formatTime = useCallback((seconds: number) => {
    const mins = Math.floor(Math.abs(seconds) / 60);
    const secs = Math.abs(seconds) % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const isNoTimerMode = session.planned_duration_minutes >= 480;
  const remaining = planned - elapsed;
  const isOvertime = !isNoTimerMode && remaining < 0;

  return (
    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
      <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-mono ${
        isOvertime ? 'bg-red-500/20 text-red-400' : isPaused ? 'bg-yellow-500/20 text-yellow-400' : 'bg-primary-500/20 text-primary-400'
      }`}>
        <Timer className="w-3 h-3" />
        <span className="tabular-nums">
          {isOvertime && '+'}
          {isNoTimerMode ? formatTime(elapsed) : formatTime(isOvertime ? -remaining : remaining)}
        </span>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); (isPaused ? onResume : onPause)(); }}
        className={`w-6 h-6 rounded flex items-center justify-center ${
          isPaused ? 'bg-primary-500/20 text-primary-400' : 'bg-yellow-500/20 text-yellow-400'
        }`}
      >
        {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onComplete(); }}
        className="w-6 h-6 rounded bg-green-500/20 text-green-400 flex items-center justify-center"
      >
        <CheckCircle2 className="w-3 h-3" />
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onStop(); }}
        className="w-6 h-6 rounded bg-gray-500/20 text-gray-400 flex items-center justify-center"
      >
        <Square className="w-3 h-3" />
      </button>
    </div>
  );
}

function TaskCardCompact({
  task,
  onClick,
  onStart,
  onCompleteTask,
  activeSession,
  onPause,
  onResume,
  onComplete,
  onStop,
}: {
  task: { id: number; title: string; progress_percent: number; estimated_minutes?: number; status: string; subtasks_count: number };
  onClick: () => void;
  onStart?: () => void;
  onCompleteTask?: () => void;
  activeSession?: FocusSession;
  onPause?: () => void;
  onResume?: () => void;
  onComplete?: () => void;
  onStop?: () => void;
}) {
  const isCompleted = task.status === 'completed';
  const hasSubtasks = task.subtasks_count > 0;
  const hasActiveSession = !!activeSession;

  return (
    <div
      className={`bg-dark-700/50 rounded-xl p-3 border ${hasActiveSession ? 'border-primary-500/50' : 'border-gray-800'} ${isCompleted ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-3" onClick={onClick}>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isCompleted ? 'bg-green-500/20' : hasActiveSession ? 'bg-primary-500/30' : 'bg-purple-500/20'
        }`}>
          {isCompleted ? (
            <span className="text-sm text-green-400">✓</span>
          ) : hasActiveSession ? (
            <div className="w-3 h-3 rounded-full bg-primary-500 animate-pulse" />
          ) : (
            <Sparkles className="w-4 h-4 text-purple-400" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={`text-sm font-medium ${isCompleted ? 'text-gray-500 line-through' : 'text-white'}`}>
            {task.title}
          </h3>
          {!isCompleted && hasSubtasks && !hasActiveSession && (
            <div className="mt-1 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{ width: `${task.progress_percent}%` }}
              />
            </div>
          )}
        </div>
        {hasActiveSession && activeSession && onPause && onResume && onComplete && onStop ? (
          <MiniTimer
            session={activeSession}
            onPause={onPause}
            onResume={onResume}
            onComplete={onComplete}
            onStop={onStop}
          />
        ) : !isCompleted && (
          <div className="flex items-center gap-1.5">
            {onCompleteTask && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCompleteTask();
                }}
                className="w-8 h-8 rounded-lg bg-green-500/20 hover:bg-green-500/30 flex items-center justify-center transition-colors flex-shrink-0"
              >
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              </button>
            )}
            {onStart && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onStart();
                }}
                className="w-8 h-8 rounded-lg bg-primary-500 hover:bg-primary-600 flex items-center justify-center transition-colors flex-shrink-0"
              >
                <Play className="w-4 h-4 text-white" fill="white" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { t, language, setLanguage } = useLanguage();
  const { user, isLoading, latestMood, setLatestMood, showMoodModal, setShowMoodModal, showXPAnimation, setActiveSession, setActiveSessions, activeSessions, removeActiveSession, updateActiveSession, isTelegramEnvironment, isSpotlightActive } = useAppStore();
  const [moodLoading, setMoodLoading] = useState(false);

  // Modal phase queue: ensures modals show one at a time
  // catchup → dailyBonus → mood → done
  const [modalPhase, setModalPhase] = useState<'catchup' | 'dailyBonus' | 'mood' | 'done'>('catchup');

  // Fetch active focus sessions so timers survive page navigation
  const { data: activeSessionsData } = useQuery({
    queryKey: ['focus', 'active'],
    queryFn: () => focusService.getActiveSession(),
    enabled: !!user,
    refetchInterval: 30000, // Sync every 30s
  });

  useEffect(() => {
    if (activeSessionsData?.data?.sessions) {
      setActiveSessions(activeSessionsData.data.sessions);
    }
  }, [activeSessionsData, setActiveSessions]);

  // Retroactive level rewards catch-up (one-shot on first load)
  const catchUpCheckedRef = useRef(false);
  useEffect(() => {
    if (!user || catchUpCheckedRef.current) return;
    catchUpCheckedRef.current = true;
    cardsService.claimLevelCatchUp().then((result) => {
      // Store energy limit increase if present (will show after level-up modal)
      if (result.data?.energy_limit_increased) {
        setEnergyLimitData({
          old_max: result.data.energy_limit_increased.old_max,
          new_max: result.data.energy_limit_increased.new_max,
        });
      }

      if (result.success && result.data?.has_rewards) {
        setLevelUpData({
          newLevel: result.data.new_level || 0,
          rewards: result.data.rewards,
          genreUnlockAvailable: result.data.genre_unlock_available || null,
        });
        setShowLevelUpModal(true);
        // Phase advances when level-up modal closes (see onClose handler)
      } else if (result.data?.energy_limit_increased) {
        // No regular rewards but energy limit increased — show dedicated modal
        setShowEnergyLimitModal(true);
      } else {
        // No catch-up rewards — check if user has pending genre unlocks
        cardsService.getUnlockedGenres().then((genreResult) => {
          if (genreResult.success && genreResult.data?.unlock_available?.can_unlock) {
            setLevelUpData({
              newLevel: user.level || 0,
              rewards: [],
              genreUnlockAvailable: genreResult.data.unlock_available,
            });
            setShowLevelUpModal(true);
          } else {
            // No level-up to show → advance to daily bonus phase
            setModalPhase('dailyBonus');
          }
        }).catch(() => {
          setModalPhase('dailyBonus');
        });
      }
    }).catch(() => {
      catchUpCheckedRef.current = false;
      setModalPhase('dailyBonus');
    });
  }, [user]);

  // Date selection with smart focus:
  // - If last visit was today: restore last selected date
  // - If last visit was another day: focus on today
  const [selectedDate, setSelectedDate] = useState(() => {
    if (typeof window === 'undefined') return new Date();

    const today = formatDateForAPI(new Date());
    const lastVisitDate = localStorage.getItem('moodsprint_last_visit_date');
    const lastSelectedDate = localStorage.getItem('moodsprint_last_selected_date');

    if (lastVisitDate === today && lastSelectedDate) {
      // Same day visit - restore last selected date
      const parsed = new Date(lastSelectedDate);
      if (!isNaN(parsed.getTime())) {
        return parsed;
      }
    }

    // New day or first visit - use today
    return new Date();
  });

  // Save last visit date and selected date to localStorage
  useEffect(() => {
    const today = formatDateForAPI(new Date());
    localStorage.setItem('moodsprint_last_visit_date', today);
  }, []);

  // Save selected date when it changes
  useEffect(() => {
    localStorage.setItem('moodsprint_last_selected_date', formatDateForAPI(selectedDate));
  }, [selectedDate]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [postponeNotificationDismissed, setPostponeNotificationDismissed] = useState(false);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>(() => {
    if (typeof window === 'undefined') return 'pending';
    const stored = localStorage.getItem('moodsprint_filter_status');
    if (stored === 'pending' || stored === 'in_progress' || stored === 'completed' || stored === 'all') {
      return stored as FilterStatus;
    }
    return 'pending';
  });
  // Persist filter status
  useEffect(() => {
    localStorage.setItem('moodsprint_filter_status', filterStatus);
  }, [filterStatus]);

  const [earnedCard, setEarnedCard] = useState<EarnedCard | null>(null);
  const [showCardModal, setShowCardModal] = useState(false);
  const [showCardTutorial, setShowCardTutorial] = useState(false);
  const [showLevelUpModal, setShowLevelUpModal] = useState(false);
  const [levelUpData, setLevelUpData] = useState<{
    newLevel: number;
    rewards: LevelRewardItem[];
    genreUnlockAvailable?: { can_unlock: boolean; available_genres: string[]; suggested_genres?: string[] } | null;
  } | null>(null);
  const [showEnergyLimitModal, setShowEnergyLimitModal] = useState(false);
  const [energyLimitData, setEnergyLimitData] = useState<{ old_max: number; new_max: number } | null>(null);
  const [showStreakMilestoneModal, setShowStreakMilestoneModal] = useState(false);
  const [streakMilestoneData, setStreakMilestoneData] = useState<{ milestone_days: number; xp_bonus: number; card_earned?: { id: number; name: string; emoji: string; rarity: string } } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCompactMode, setIsCompactMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('taskListCompact');
      // Default to compact mode if not explicitly set to 'false'
      return stored !== 'false';
    }
    return true;
  });
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [isScrolled, setIsScrolled] = useState(false);
  // Track if this is user's first visit (to skip daily bonus & mood on first login)
  const [isFirstVisit, setIsFirstVisit] = useState(() => {
    if (typeof window !== 'undefined') {
      return !localStorage.getItem('first_visit_completed');
    }
    return false;
  });

  // Check if this is the first day - skip mood check on first day entirely
  const isFirstDay = typeof window !== 'undefined' && (() => {
    const firstLoginDate = localStorage.getItem('first_login_date');
    if (!firstLoginDate) return true; // No date set = first day
    return firstLoginDate === new Date().toDateString();
  })();

  const selectedDateStr = formatDateForAPI(selectedDate);

  // Calculate week date range for task counts
  const weekDates = useMemo(() => {
    const today = new Date();
    const currentDay = today.getDay();
    const dates: string[] = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() - currentDay + i);
      dates.push(formatDateForAPI(date));
    }
    return dates;
  }, []);

  // Check if we should show mood modal — only when modal queue reaches 'mood' phase
  useEffect(() => {
    if (modalPhase !== 'mood') return;
    if (user && !latestMood && !isFirstVisit && !isFirstDay && !isSpotlightActive) {
      moodService.getLatestMood().then((result) => {
        if (result.success && result.data?.mood_check) {
          setLatestMood(result.data.mood_check);
        } else {
          setShowMoodModal(true);
        }
      });
    }
    setModalPhase('done');
  }, [modalPhase, user, latestMood, setLatestMood, setShowMoodModal, isFirstVisit, isFirstDay, isSpotlightActive]);

  // Fallback: mark first visit as completed if spotlight isn't showing
  // (This handles edge case where onboarding_home is set but first_visit_completed isn't)
  useEffect(() => {
    if (isFirstVisit && user && !isSpotlightActive) {
      // If spotlight isn't active after 2 seconds, mark first visit as done
      const timer = setTimeout(() => {
        localStorage.setItem('first_visit_completed', 'true');
        setIsFirstVisit(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [isFirstVisit, user, isSpotlightActive]);

  // Track scroll for header overlay
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Query tasks for selected date with status filter
  const { data: tasksData, isLoading: tasksLoading, isFetching } = useQuery({
    queryKey: ['tasks', 'by_date', selectedDateStr, filterStatus],
    queryFn: () => tasksService.getTasks({
      due_date: selectedDateStr,
      ...(filterStatus !== 'all' && { status: filterStatus }),
      limit: 100,
    }),
    enabled: !!user,
    placeholderData: keepPreviousData,
  });

  // Query all tasks for selected date to calculate status counts
  const { data: allTasksForCounts } = useQuery({
    queryKey: ['tasks', 'by_date', selectedDateStr, 'all'],
    queryFn: () => tasksService.getTasks({
      due_date: selectedDateStr,
      limit: 100,
    }),
    enabled: !!user,
    staleTime: 1000 * 30, // 30 seconds
  });

  // Calculate status counts for badges
  const statusCounts = useMemo(() => {
    const tasks = allTasksForCounts?.data?.tasks || [];
    return {
      pending: tasks.filter(t => t.status === 'pending').length,
      in_progress: tasks.filter(t => t.status === 'in_progress').length,
      completed: tasks.filter(t => t.status === 'completed').length,
    };
  }, [allTasksForCounts]);

  // Query week tasks for calendar badges (reuse main query data when possible)
  const { data: weekTasksData } = useQuery({
    queryKey: ['tasks', 'week', weekDates[0], weekDates[6]],
    queryFn: () => tasksService.getTasks({
      due_date_from: weekDates[0],
      due_date_to: weekDates[6],
      limit: 100,
    }),
    enabled: !!user,
    staleTime: 1000 * 60 * 5, // 5 minutes - less frequent refresh
  });

  // Calculate task counts per day for the week
  const taskCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    const allTasks = weekTasksData?.data?.tasks || [];
    for (const task of allTasks) {
      if (task.due_date && task.status !== 'completed') {
        counts[task.due_date] = (counts[task.due_date] || 0) + 1;
      }
    }
    return counts;
  }, [weekTasksData]);

  const createMutation = useMutation({
    mutationFn: async (input: { title: string; description: string; due_date: string; scheduled_at?: string; autoDecompose?: boolean; subtasks?: string[] }) => {
      const result = await tasksService.createTask(input);
      if (result.success && result.data?.task) {
        const taskId = result.data.task.id;
        // Create manual subtasks if provided
        if (input.subtasks && input.subtasks.length > 0) {
          for (const subtaskTitle of input.subtasks) {
            try {
              await tasksService.createSubtask(taskId, { title: subtaskTitle.trim() });
            } catch (err) {
              console.error('[CreateSubtask] Failed:', err);
            }
          }
        }
        // Auto-decompose the task after creation (only if no manual subtasks)
        if (input.autoDecompose && (!input.subtasks || input.subtasks.length === 0)) {
          try {
            const decomposeResult = await tasksService.decomposeTask(taskId, latestMood?.id);
            if (decomposeResult.success) {
              queryClient.invalidateQueries({ queryKey: ['tasks'] });
            }
          } catch (err) {
            console.error('[AutoDecompose] Failed:', err);
          }
        }
      }
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowCreateModal(false);
      hapticFeedback('success');
    },
  });

  const startFocusMutation = useMutation({
    mutationFn: (taskId: number) =>
      focusService.startSession({
        task_id: taskId,
        planned_duration_minutes: 25,
      }),
    onSuccess: (result) => {
      if (result.success && result.data) {
        setActiveSession(result.data.session);
        hapticFeedback('success');
      }
    },
  });

  const pauseSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.pauseSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
      }
    },
  });

  const resumeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.resumeSession(),
    onSuccess: (result) => {
      if (result.success && result.data?.session) {
        updateActiveSession(result.data.session);
        queryClient.invalidateQueries({ queryKey: ['focus', 'active'] });
      }
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.completeSession(sessionId, true),
    onSuccess: (result, sessionId) => {
      removeActiveSession(sessionId);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      if (result.data?.xp_earned) showXPAnimation(result.data.xp_earned);
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard({
          ...result.data.card_earned,
          quick_completion: result.data.quick_completion,
          quick_completion_message: result.data.quick_completion_message,
        } as EarnedCard);
        setShowCardModal(true);
      }
      // Level-up rewards
      if (result.data?.level_up) {
        setLevelUpData({
          newLevel: result.data.new_level || 0,
          rewards: result.data.level_rewards || [],
          genreUnlockAvailable: result.data.genre_unlock_available || null,
        });
        if (!result.data?.card_earned) setShowLevelUpModal(true);
      }
      // Streak milestone
      if (result.data?.streak_milestone) {
        setStreakMilestoneData(result.data.streak_milestone);
        setShowStreakMilestoneModal(true);
      }
      hapticFeedback('success');
    },
  });

  const cancelSessionMutation = useMutation({
    mutationFn: (sessionId: number) => focusService.cancelSession(sessionId),
    onSuccess: (result, sessionId) => {
      removeActiveSession(sessionId);
      queryClient.invalidateQueries({ queryKey: ['focus'] });
      hapticFeedback('light');
    },
  });

  const completeTaskMutation = useMutation({
    mutationFn: (taskId: number) => tasksService.updateTask(taskId, { status: 'completed' }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['user', 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      if (result.data?.xp_earned) showXPAnimation(result.data.xp_earned);
      // Show card earned modal if card was generated
      if (result.data?.card_earned) {
        setEarnedCard({
          ...result.data.card_earned,
          quick_completion: result.data.quick_completion,
          quick_completion_message: result.data.quick_completion_message,
        } as EarnedCard);
        setShowCardModal(true);
      }
      // Level-up rewards
      if (result.data?.level_up) {
        setLevelUpData({
          newLevel: result.data.new_level || 0,
          rewards: result.data.level_rewards || [],
          genreUnlockAvailable: result.data.genre_unlock_available || null,
        });
        if (!result.data?.card_earned) setShowLevelUpModal(true);
      }
      // Streak milestone
      if (result.data?.streak_milestone) {
        setStreakMilestoneData(result.data.streak_milestone);
        setShowStreakMilestoneModal(true);
      }
      hapticFeedback('success');
    },
  });

  // Helper to get session for a task
  const getSessionForTask = (taskId: number) => {
    return activeSessions.find(s => s.task_id === taskId);
  };

  const handleCreateTask = (title: string, description: string, dueDate: string, scheduledAt?: string, autoDecompose?: boolean, subtasks?: string[]) => {
    createMutation.mutate({ title, description, due_date: dueDate, scheduled_at: scheduledAt, autoDecompose, subtasks });
  };

  // Toggle compact mode
  const toggleCompactMode = useCallback(() => {
    setIsCompactMode(prev => {
      const newValue = !prev;
      localStorage.setItem('taskListCompact', String(newValue));
      return newValue;
    });
    hapticFeedback('light');
  }, []);

  // Toggle collapsed group
  const toggleGroup = useCallback((priority: string) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [priority]: !prev[priority],
    }));
    hapticFeedback('light');
  }, []);

  // Check for postponed tasks notification
  const { data: postponeData } = useQuery({
    queryKey: ['tasks', 'postpone-status'],
    queryFn: () => tasksService.getPostponeStatus(),
    enabled: !!user,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  const handleMoodSubmit = async (mood: MoodLevel, energy: EnergyLevel, note?: string) => {
    setMoodLoading(true);
    try {
      const result = await moodService.createMoodCheck({ mood, energy, note });
      if (result.success && result.data) {
        setLatestMood(result.data.mood_check);
        setShowMoodModal(false);
        hapticFeedback('success');
        if (result.data.xp_earned) {
          showXPAnimation(result.data.xp_earned);
        }
      }
    } catch (error) {
      console.error('Failed to log mood:', error);
    } finally {
      setMoodLoading(false);
    }
  };

  const allTasks = tasksData?.data?.tasks || [];
  const postponeStatus = postponeData?.data;
  const showPostponeNotification = postponeStatus?.has_postponed && !postponeNotificationDismissed;

  // Filter tasks by search query (must be before early returns)
  const filteredTasks = useMemo(() => {
    if (!searchQuery.trim()) return allTasks;
    const query = searchQuery.toLowerCase();
    return allTasks.filter(task => task.title.toLowerCase().includes(query));
  }, [allTasks, searchQuery]);

  // Group tasks by priority (must be before early returns)
  const groupedTasks = useMemo(() => {
    const groups: Record<'high' | 'medium' | 'low', typeof allTasks> = {
      high: [],
      medium: [],
      low: [],
    };
    for (const task of filteredTasks) {
      const priority = (task.priority || 'medium') as 'high' | 'medium' | 'low';
      groups[priority].push(task);
    }
    return groups;
  }, [filteredTasks]);

  const priorityConfig = {
    high: { label: t('highPriority'), color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' },
    medium: { label: t('mediumPriority'), color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
    low: { label: t('lowPriority'), color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/30' },
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    // Mobile app handles its own auth - just show loading
    if (isMobileApp()) {
      return (
        <div className="flex items-center justify-center h-screen">
          <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
        </div>
      );
    }

    // Show full landing page with login/register for non-Telegram browser users
    if (!isTelegramEnvironment) {
      return <LandingPage />;
    }

    // In Telegram but not authenticated - show simple message
    return (
      <div className="flex flex-col items-center justify-center h-screen p-6 text-center">
        <div className="w-48 h-48 mb-8 relative animate-float">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-purple-500/30 to-blue-500/30 blur-2xl" />
          <div className="absolute inset-4 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 animate-pulse-glow" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">
          MoodSprint
        </h1>
        <p className="text-gray-400 mb-8 max-w-xs">
          {t('personalAssistantDesc')}
        </p>
        <Button variant="gradient" size="lg" className="w-full max-w-xs">
          <Sparkles className="w-5 h-5" />
          {t('openInTelegram')}
        </Button>
        <p className="text-xs text-gray-500 mt-4">
          {t('telegramOnlyHint')}
        </p>
      </div>
    );
  }

  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return t('goodMorning');
    if (hour < 17) return t('goodAfternoon');
    return t('goodEvening');
  };

  // Toggle language
  const toggleLanguage = () => {
    const newLang = language === 'ru' ? 'en' : 'ru';
    setLanguage(newLang);
    // Invalidate all cached queries to refetch with new language
    queryClient.invalidateQueries();
    hapticFeedback('light');
  };

  return (
    <SpotlightOnboarding steps={ONBOARDING_STEPS} storageKey="home">
    <div className="relative">
      {/* Scroll overlay with blur */}
      <ScrollBackdrop />
    <div className="p-4 space-y-6">
      {/* Daily Bonus Modal — only enabled when modal phase reaches it */}
      <DailyBonus
        enabled={modalPhase === 'dailyBonus'}
        onDone={() => setModalPhase('mood')}
      />

      {/* Postponed Tasks Notification */}
      {showPostponeNotification && postponeStatus && (
        <div className="bg-amber-500/20 border border-amber-500/30 rounded-xl p-3 flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-amber-500/30 flex items-center justify-center flex-shrink-0">
            <ArrowUp className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-amber-200">{postponeStatus.message}</p>
            {postponeStatus.priority_changes && postponeStatus.priority_changes.length > 0 && (
              <div className="mt-1 text-xs text-amber-400/80">
                {t('priorityRaised')}: {postponeStatus.priority_changes.map(c => c.task_title).join(', ')}
              </div>
            )}
          </div>
          <button
            onClick={() => setPostponeNotificationDismissed(true)}
            className="p-1 text-amber-400 hover:text-amber-300 transition-colors flex-shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {getGreeting()},
          </h1>
          <p className="text-gray-400">{user.first_name || t('friend')}</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="w-10 h-10 rounded-full bg-dark-700 border border-gray-700 flex items-center justify-center hover:bg-dark-600 transition-colors text-sm font-medium"
          >
            {language === 'ru' ? '🇷🇺' : '🇬🇧'}
          </button>
          {/* Streak Indicator */}
          {user.streak_days > 0 && <StreakIndicator days={user.streak_days} />}
          {/* Mood Button */}
          <button
            onClick={() => setShowMoodModal(true)}
            className="w-10 h-10 rounded-full bg-dark-700 border border-gray-700 flex items-center justify-center hover:bg-dark-600 transition-colors"
            data-onboarding="mood-check"
          >
            {latestMood ? (
              <span className="text-lg">
                {MOOD_EMOJIS[latestMood.mood as keyof typeof MOOD_EMOJIS]}
              </span>
            ) : (
              <Smile className="w-5 h-5 text-gray-400" />
            )}
          </button>
          {/* Avatar - click to go to profile */}
          <button onClick={() => router.push('/profile')} className="focus:outline-none">
            {user.photo_url ? (
              <img
                src={user.photo_url}
                alt={user.first_name || 'User'}
                className="w-12 h-12 rounded-full object-cover border-2 border-purple-500/50"
              />
            ) : (
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">
                {(user.first_name?.[0] || '?').toUpperCase()}
              </div>
            )}
          </button>
        </div>
      </div>

      {/* Week Calendar */}
      <WeekCalendar
        selectedDate={selectedDate}
        onDateSelect={setSelectedDate}
        language={language}
        taskCounts={taskCounts}
      />

      {/* Tasks Section */}
      <div className="space-y-3 min-h-[180px]">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white capitalize">{formatDateDisplay(selectedDate, language, t)}</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleCompactMode}
              className="p-2 rounded-lg bg-gray-700/50 hover:bg-gray-600/50 transition-colors"
              title={isCompactMode ? t('normalView') : t('compactView')}
            >
              {isCompactMode ? <LayoutGrid className="w-4 h-4 text-gray-400" /> : <List className="w-4 h-4 text-gray-400" />}
            </button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowCreateModal(true)}
              data-onboarding="create-task"
            >
              <Plus className="w-4 h-4 mr-1" />
              {t('add')}
            </Button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('searchTasks')}
            className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-xl text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-600 rounded"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>

        {/* Status Filters */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide md:overflow-x-visible md:flex-wrap">
          {([
            { value: 'pending' as const, labelKey: 'statusPending' as const },
            { value: 'in_progress' as const, labelKey: 'statusInProgress' as const },
            { value: 'completed' as const, labelKey: 'statusCompleted' as const },
            { value: 'all' as const, labelKey: 'all' as const },
          ]).map((filter) => {
            const count = filter.value !== 'all' ? statusCounts[filter.value] : 0;
            const showBadge = filter.value !== 'all' && count > 0;

            return (
              <button
                key={filter.value}
                onClick={() => setFilterStatus(filter.value)}
                className={`relative px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  filterStatus === filter.value
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {t(filter.labelKey)}
                {showBadge && (
                  <span className={`ml-1.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold ${
                    filterStatus === filter.value
                      ? 'bg-white/20 text-white'
                      : 'bg-primary-500/80 text-white'
                  }`}>
                    {count > 99 ? '99+' : count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {tasksLoading && !tasksData ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="glass" className="h-14 animate-pulse" />
            ))}
          </div>
        ) : filteredTasks.length > 0 ? (
          <div className="space-y-3">
            {(['high', 'medium', 'low'] as const).map((priority) => {
              const tasks = groupedTasks[priority];
              if (tasks.length === 0) return null;
              const config = priorityConfig[priority];
              const isCollapsed = collapsedGroups[priority];

              return (
                <div key={priority} className={`rounded-xl border ${config.border} overflow-hidden`}>
                  {/* Group Header */}
                  <button
                    onClick={() => toggleGroup(priority)}
                    className={`w-full flex items-center justify-between px-3 py-2 ${config.bg} hover:opacity-90 transition-opacity`}
                  >
                    <div className="flex items-center gap-2">
                      {isCollapsed ? (
                        <ChevronRight className={`w-4 h-4 ${config.color}`} />
                      ) : (
                        <ChevronDown className={`w-4 h-4 ${config.color}`} />
                      )}
                      <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
                    </div>
                    <span className="text-xs text-gray-400">{tasks.length} {t('tasksCount')}</span>
                  </button>

                  {/* Group Content */}
                  {!isCollapsed && (
                    <div className={`${isCompactMode ? 'divide-y divide-gray-800' : 'p-2 space-y-2'}`}>
                      {tasks.map((task) => {
                        const session = getSessionForTask(task.id);

                        if (isCompactMode) {
                          // Ultra compact row
                          return (
                            <div
                              key={task.id}
                              onClick={() => router.push(`/tasks/${task.id}`)}
                              className={`flex items-center gap-2 px-3 py-2 hover:bg-gray-800/50 cursor-pointer ${task.status === 'completed' ? 'opacity-50' : ''}`}
                            >
                              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                                task.status === 'completed' ? 'bg-green-500' : 'bg-purple-500'
                              }`} />
                              <span className={`text-sm flex-1 min-w-0 ${task.status === 'completed' ? 'text-gray-500 line-through' : 'text-white'}`}>
                                {task.title}
                              </span>
                              {task.status !== 'completed' && session && (
                                <MiniTimer
                                  session={session}
                                  onPause={() => pauseSessionMutation.mutate(session.id)}
                                  onResume={() => resumeSessionMutation.mutate(session.id)}
                                  onComplete={() => completeTaskMutation.mutate(task.id)}
                                  onStop={() => cancelSessionMutation.mutate(session.id)}
                                />
                              )}
                              {task.status !== 'completed' && !session && (
                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      completeTaskMutation.mutate(task.id);
                                    }}
                                    className="p-1 rounded bg-green-500/20 hover:bg-green-500/30 flex-shrink-0"
                                  >
                                    <CheckCircle2 className="w-3 h-3 text-green-400" />
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      startFocusMutation.mutate(task.id);
                                    }}
                                    className="p-1 rounded bg-primary-500/20 hover:bg-primary-500/30 flex-shrink-0"
                                  >
                                    <Play className="w-3 h-3 text-primary-400" fill="currentColor" />
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        }

                        // Normal card
                        return (
                          <TaskCardCompact
                            key={task.id}
                            task={task}
                            onClick={() => router.push(`/tasks/${task.id}`)}
                            onStart={task.status !== 'completed' && !session ? () => startFocusMutation.mutate(task.id) : undefined}
                            onCompleteTask={task.status !== 'completed' && !session ? () => completeTaskMutation.mutate(task.id) : undefined}
                            activeSession={session}
                            onPause={session ? () => pauseSessionMutation.mutate(session.id) : undefined}
                            onResume={session ? () => resumeSessionMutation.mutate(session.id) : undefined}
                            onComplete={session ? () => completeTaskMutation.mutate(task.id) : undefined}
                            onStop={session ? () => cancelSessionMutation.mutate(session.id) : undefined}
                          />
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <Card variant="glass" className="text-center py-8">
            <Sparkles className="w-12 h-12 text-purple-400 mx-auto mb-3" />
            <p className="text-gray-400 mb-4">
              {searchQuery
                ? t('noTasksInCategory')
                : filterStatus === 'all'
                ? `${t('noTasksForDate')} ${formatDateDisplay(selectedDate, language, t).toLowerCase()}`
                : t('noTasksInCategory')}
            </p>
            <Button variant="gradient" onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4" />
              {t('createTask')}
            </Button>
          </Card>
        )}
      </div>

      {/* Mood Modal */}
      <Modal
        isOpen={showMoodModal}
        onClose={() => setShowMoodModal(false)}
        title={t('howAreYouFeeling')}
      >
        <MoodSelector onSubmit={handleMoodSubmit} isLoading={moodLoading} />
      </Modal>

      {/* Create Task Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title={t('createTask')}
      >
        <TaskForm
          onSubmit={handleCreateTask}
          isLoading={createMutation.isPending}
          initialDueDate={selectedDateStr}
        />
      </Modal>

      {/* Card Earned Modal */}
      <CardEarnedModal
        isOpen={showCardModal}
        card={earnedCard}
        onClose={() => {
          setShowCardModal(false);
          setEarnedCard(null);
          // Show level-up modal after card modal if there was a level up
          if (levelUpData) {
            setShowLevelUpModal(true);
          } else if (shouldShowCardTutorial()) {
            setShowCardTutorial(true);
          }
        }}
        t={t}
      />

      {/* Level Up Modal */}
      {levelUpData && (
        <LevelUpModal
          isOpen={showLevelUpModal}
          onClose={() => {
            setShowLevelUpModal(false);
            setLevelUpData(null);
            queryClient.invalidateQueries({ queryKey: ['cards'] });
            // Show energy limit modal if pending
            if (energyLimitData) {
              setShowEnergyLimitModal(true);
              return;
            }
            // Advance modal queue to next phase
            if (modalPhase === 'catchup') {
              setModalPhase('dailyBonus');
            }
            if (shouldShowCardTutorial()) {
              setShowCardTutorial(true);
            }
          }}
          newLevel={levelUpData.newLevel}
          rewards={levelUpData.rewards}
          genreUnlockAvailable={levelUpData.genreUnlockAvailable}
          onGenreSelect={() => {
            queryClient.invalidateQueries({ queryKey: ['cards'] });
          }}
        />
      )}

      {/* Energy Limit Modal */}
      {energyLimitData && (
        <EnergyLimitModal
          isOpen={showEnergyLimitModal}
          onClose={() => {
            setShowEnergyLimitModal(false);
            setEnergyLimitData(null);
            queryClient.invalidateQueries({ queryKey: ['campaign'] });
            // Advance modal queue to next phase
            if (modalPhase === 'catchup') {
              setModalPhase('dailyBonus');
            }
            if (shouldShowCardTutorial()) {
              setShowCardTutorial(true);
            }
          }}
          oldMax={energyLimitData.old_max}
          newMax={energyLimitData.new_max}
        />
      )}

      {/* Streak Milestone Modal */}
      <StreakMilestoneModal
        isOpen={showStreakMilestoneModal}
        onClose={() => {
          setShowStreakMilestoneModal(false);
          setStreakMilestoneData(null);
        }}
        milestone={streakMilestoneData}
      />

      {/* Card Tutorial (first-time onboarding) */}
      <CardTutorial
        isOpen={showCardTutorial}
        onClose={() => setShowCardTutorial(false)}
      />
    </div>
    </div>
    </SpotlightOnboarding>
  );
}
