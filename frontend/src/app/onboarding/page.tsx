'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, Card } from '@/components/ui';
import { onboardingService, gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback } from '@/lib/telegram';
import type { OnboardingInput } from '@/domain/types';
import type { Genre } from '@/services/gamification';

type Step = 'time' | 'tasks' | 'challenges' | 'genre' | 'goals' | 'result';

const timeOptions = [
  { value: 'morning', label: 'Утро', emoji: '🌅', desc: '6:00 - 12:00' },
  { value: 'afternoon', label: 'День', emoji: '☀️', desc: '12:00 - 18:00' },
  { value: 'evening', label: 'Вечер', emoji: '🌆', desc: '18:00 - 22:00' },
  { value: 'night', label: 'Ночь', emoji: '🌙', desc: '22:00 - 6:00' },
  { value: 'varies', label: 'По-разному', emoji: '🔄', desc: 'Зависит от дня' },
] as const;

const taskOptions = [
  { value: 'creative', label: 'Творческие', emoji: '🎨' },
  { value: 'analytical', label: 'Аналитические', emoji: '📊' },
  { value: 'communication', label: 'Общение', emoji: '💬' },
  { value: 'physical', label: 'Физические', emoji: '💪' },
  { value: 'learning', label: 'Обучение', emoji: '📚' },
  { value: 'planning', label: 'Планирование', emoji: '📋' },
  { value: 'coding', label: 'Программирование', emoji: '💻' },
  { value: 'writing', label: 'Письмо', emoji: '✍️' },
];

const challengeOptions = [
  { value: 'focus', label: 'Сложно сфокусироваться', emoji: '🎯' },
  { value: 'procrastination', label: 'Прокрастинация', emoji: '⏰' },
  { value: 'overwhelm', label: 'Перегруз задачами', emoji: '😵' },
  { value: 'energy', label: 'Нехватка энергии', emoji: '🔋' },
  { value: 'motivation', label: 'Низкая мотивация', emoji: '💫' },
  { value: 'perfectionism', label: 'Перфекционизм', emoji: '✨' },
  { value: 'starting', label: 'Сложно начать', emoji: '🚀' },
  { value: 'finishing', label: 'Не довожу до конца', emoji: '🏁' },
];

const genreOptions: { value: Genre; label: string; emoji: string; desc: string }[] = [
  {
    value: 'magic',
    label: 'Магия',
    emoji: '🧙‍♂️',
    desc: 'Как в Гарри Поттере',
  },
  {
    value: 'fantasy',
    label: 'Фэнтези',
    emoji: '⚔️',
    desc: 'Как Властелин Колец',
  },
  {
    value: 'scifi',
    label: 'Научная фантастика',
    emoji: '🚀',
    desc: 'Космические приключения',
  },
  {
    value: 'cyberpunk',
    label: 'Киберпанк',
    emoji: '🌆',
    desc: 'Мир хакеров и технологий',
  },
  {
    value: 'anime',
    label: 'Аниме',
    emoji: '🎌',
    desc: 'Японские приключения',
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { onboardingCompleted, setOnboardingCompleted } = useAppStore();
  const [step, setStep] = useState<Step>('time');
  const [selectedGenre, setSelectedGenre] = useState<Genre>('fantasy');
  const [data, setData] = useState<OnboardingInput>({
    productive_time: 'morning',
    favorite_tasks: [],
    challenges: [],
    work_description: '',
    goals: '',
  });
  const [result, setResult] = useState<{
    message: string;
    tips: string[];
  } | null>(null);

  // Check if onboarding is already completed
  const { data: statusData } = useQuery({
    queryKey: ['onboarding', 'status'],
    queryFn: () => onboardingService.getStatus(),
  });

  // Redirect if already completed
  useEffect(() => {
    if (statusData?.data?.completed || onboardingCompleted) {
      router.replace('/');
    }
  }, [statusData?.data?.completed, onboardingCompleted, router]);

  const genreMutation = useMutation({
    mutationFn: (genre: Genre) => gamificationService.setGenre(genre),
    onSuccess: () => {
      hapticFeedback('light');
    },
  });

  const completeMutation = useMutation({
    mutationFn: async (input: OnboardingInput) => {
      // First save genre preference
      await gamificationService.setGenre(selectedGenre);
      // Then complete onboarding
      return onboardingService.complete(input);
    },
    onSuccess: (response) => {
      if (response.success && response.data) {
        setResult({
          message: response.data.welcome_message,
          tips: response.data.analysis.personalized_tips,
        });
        setOnboardingCompleted(true);
        setStep('result');
        hapticFeedback('success');
      }
    },
  });

  const handleTimeSelect = (time: OnboardingInput['productive_time']) => {
    setData({ ...data, productive_time: time });
    hapticFeedback('light');
    setStep('tasks');
  };

  const handleTaskToggle = (task: string) => {
    const tasks = data.favorite_tasks.includes(task)
      ? data.favorite_tasks.filter((t) => t !== task)
      : [...data.favorite_tasks, task];
    setData({ ...data, favorite_tasks: tasks });
    hapticFeedback('light');
  };

  const handleChallengeToggle = (challenge: string) => {
    const challenges = data.challenges.includes(challenge)
      ? data.challenges.filter((c) => c !== challenge)
      : [...data.challenges, challenge];
    setData({ ...data, challenges: challenges });
    hapticFeedback('light');
  };

  const handleGenreSelect = (genre: Genre) => {
    setSelectedGenre(genre);
    hapticFeedback('light');
  };

  const handleComplete = () => {
    completeMutation.mutate(data);
  };

  const handleFinish = () => {
    router.push('/');
  };

  const progressSteps = ['time', 'tasks', 'challenges', 'genre', 'goals'] as const;
  const currentStepIndex = progressSteps.indexOf(step as typeof progressSteps[number]);

  return (
    <div className="h-screen flex flex-col pt-safe overflow-hidden">
      {/* Progress - fixed at top */}
      <div className="flex gap-1 px-4 pt-4 pb-2 flex-shrink-0">
        {progressSteps.map((s, i) => (
          <div
            key={s}
            className={`flex-1 h-1 rounded-full transition-colors ${
              currentStepIndex >= i || step === 'result'
                ? 'bg-primary-500'
                : 'bg-gray-700'
            }`}
          />
        ))}
      </div>

      {/* Step: Time */}
      {step === 'time' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white mb-2">
                Когда ты наиболее продуктивен?
              </h1>
              <p className="text-gray-400">
                Это поможет нам лучше планировать твои задачи
              </p>
            </div>

            <div className="space-y-3 pb-4">
              {timeOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleTimeSelect(opt.value)}
                  className={`w-full p-4 rounded-2xl text-left transition-all ${
                    data.productive_time === opt.value
                      ? 'bg-primary-500/20 ring-2 ring-primary-500'
                      : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{opt.emoji}</span>
                    <div>
                      <p className="font-medium text-white">{opt.label}</p>
                      <p className="text-sm text-gray-400">{opt.desc}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step: Tasks */}
      {step === 'tasks' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white mb-2">
                Какие задачи тебе нравятся?
              </h1>
              <p className="text-gray-400">Выбери одну или несколько</p>
            </div>

            <div className="grid grid-cols-2 gap-3 pb-4">
              {taskOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleTaskToggle(opt.value)}
                  className={`p-4 rounded-2xl text-center transition-all ${
                    data.favorite_tasks.includes(opt.value)
                      ? 'bg-primary-500/20 ring-2 ring-primary-500'
                      : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  <span className="text-2xl block mb-2">{opt.emoji}</span>
                  <p className="text-sm font-medium text-white">{opt.label}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Fixed buttons */}
          <div className="flex gap-3 p-4 bg-gray-900 border-t border-gray-800 flex-shrink-0 pb-safe">
            <Button variant="secondary" onClick={() => setStep('time')}>
              Назад
            </Button>
            <Button
              className="flex-1"
              onClick={() => setStep('challenges')}
              disabled={data.favorite_tasks.length === 0}
            >
              Далее
            </Button>
          </div>
        </div>
      )}

      {/* Step: Challenges */}
      {step === 'challenges' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white mb-2">
                С чем бывают сложности?
              </h1>
              <p className="text-gray-400">Выбери что актуально для тебя</p>
            </div>

            <div className="grid grid-cols-2 gap-3 pb-4">
              {challengeOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleChallengeToggle(opt.value)}
                  className={`p-4 rounded-2xl text-center transition-all ${
                    data.challenges.includes(opt.value)
                      ? 'bg-primary-500/20 ring-2 ring-primary-500'
                      : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  <span className="text-2xl block mb-2">{opt.emoji}</span>
                  <p className="text-sm font-medium text-white">{opt.label}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Fixed buttons */}
          <div className="flex gap-3 p-4 bg-gray-900 border-t border-gray-800 flex-shrink-0 pb-safe">
            <Button variant="secondary" onClick={() => setStep('tasks')}>
              Назад
            </Button>
            <Button
              className="flex-1"
              onClick={() => setStep('genre')}
              disabled={data.challenges.length === 0}
            >
              Далее
            </Button>
          </div>
        </div>
      )}

      {/* Step: Genre */}
      {step === 'genre' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white mb-2">
                Выбери свой жанр
              </h1>
              <p className="text-gray-400">
                Это определит стиль твоих квестов и приключений
              </p>
            </div>

            <div className="space-y-3 pb-4">
              {genreOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleGenreSelect(opt.value)}
                  className={`w-full p-4 rounded-2xl text-left transition-all ${
                    selectedGenre === opt.value
                      ? 'bg-primary-500/20 ring-2 ring-primary-500'
                      : 'bg-gray-800 hover:bg-gray-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{opt.emoji}</span>
                    <div>
                      <p className="font-medium text-white">{opt.label}</p>
                      <p className="text-sm text-gray-400">{opt.desc}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Fixed buttons */}
          <div className="flex gap-3 p-4 bg-gray-900 border-t border-gray-800 flex-shrink-0 pb-safe">
            <Button variant="secondary" onClick={() => setStep('challenges')}>
              Назад
            </Button>
            <Button className="flex-1" onClick={() => setStep('goals')}>
              Далее
            </Button>
          </div>
        </div>
      )}

      {/* Step: Goals */}
      {step === 'goals' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white mb-2">
                Чего ты хочешь достичь?
              </h1>
              <p className="text-gray-400">Необязательно, но поможет нам лучше</p>
            </div>

            <div className="space-y-4 pb-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Расскажи о своей работе или учёбе
                </label>
                <textarea
                  value={data.work_description}
                  onChange={(e) =>
                    setData({ ...data, work_description: e.target.value })
                  }
                  placeholder="Например: работаю разработчиком, много задач параллельно..."
                  className="w-full p-4 bg-gray-800 rounded-2xl text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Твои цели в продуктивности
                </label>
                <textarea
                  value={data.goals}
                  onChange={(e) => setData({ ...data, goals: e.target.value })}
                  placeholder="Например: хочу лучше фокусироваться и меньше прокрастинировать..."
                  className="w-full p-4 bg-gray-800 rounded-2xl text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={3}
                />
              </div>
            </div>
          </div>

          {/* Fixed buttons */}
          <div className="flex gap-3 p-4 bg-gray-900 border-t border-gray-800 flex-shrink-0 pb-safe">
            <Button variant="secondary" onClick={() => setStep('genre')}>
              Назад
            </Button>
            <Button
              className="flex-1"
              onClick={handleComplete}
              isLoading={completeMutation.isPending}
            >
              Завершить
            </Button>
          </div>
        </div>
      )}

      {/* Step: Result */}
      {step === 'result' && result && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4">
            <div className="text-center mb-6">
              <span className="text-5xl mb-4 block">🎉</span>
              <h1 className="text-2xl font-bold text-white mb-2">Готово!</h1>
              <p className="text-gray-400">{result.message}</p>
            </div>

            {result.tips.length > 0 && (
              <Card className="mb-6">
                <h3 className="font-medium text-white mb-3">
                  Персональные советы:
                </h3>
                <ul className="space-y-2">
                  {result.tips.map((tip, i) => (
                    <li key={i} className="flex gap-2 text-sm text-gray-300">
                      <span className="text-primary-400">•</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>

          {/* Fixed button */}
          <div className="p-4 bg-gray-900 border-t border-gray-800 flex-shrink-0 pb-safe">
            <Button className="w-full" onClick={handleFinish}>
              Начать работу
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
