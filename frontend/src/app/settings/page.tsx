'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Clock, Calendar, Bell, Timer, Globe } from 'lucide-react';
import { Button, Card, ScrollBackdrop } from '@/components/ui';
import { onboardingService } from '@/services';
import { useAppStore } from '@/lib/store';
import { hapticFeedback, showBackButton, hideBackButton } from '@/lib/telegram';
import { useLanguage, Language } from '@/lib/i18n';

const DAYS_OF_WEEK = [
  { id: 1, short: 'Пн', full: 'Понедельник' },
  { id: 2, short: 'Вт', full: 'Вторник' },
  { id: 3, short: 'Ср', full: 'Среда' },
  { id: 4, short: 'Чт', full: 'Четверг' },
  { id: 5, short: 'Пт', full: 'Пятница' },
  { id: 6, short: 'Сб', full: 'Суббота' },
  { id: 7, short: 'Вс', full: 'Воскресенье' },
];

const SESSION_DURATIONS = [15, 25, 45, 60];

const LANGUAGES: { id: Language; label: string; flag: string }[] = [
  { id: 'ru', label: 'Русский', flag: '🇷🇺' },
  { id: 'en', label: 'English', flag: '🇬🇧' },
];

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAppStore();
  const { language, setLanguage, t } = useLanguage();

  const [workStartTime, setWorkStartTime] = useState('09:00');
  const [workEndTime, setWorkEndTime] = useState('18:00');
  const [workDays, setWorkDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [sessionDuration, setSessionDuration] = useState(25);
  const [reminderTime, setReminderTime] = useState('09:00');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  // Show Telegram back button
  useEffect(() => {
    const handleBack = () => router.push('/profile');
    showBackButton(handleBack);
    return () => hideBackButton();
  }, [router]);

  // Load profile data
  const { data: profileData, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => onboardingService.getProfile(),
    enabled: !!user,
  });

  // Sync state with profile data
  useEffect(() => {
    const profile = profileData?.data?.profile;
    if (profile) {
      setWorkStartTime(profile.work_start_time || '09:00');
      setWorkEndTime(profile.work_end_time || '18:00');
      setWorkDays(profile.work_days || [1, 2, 3, 4, 5]);
      setSessionDuration(profile.preferred_session_duration || 25);
      setReminderTime(profile.daily_reminder_time || '09:00');
      setNotificationsEnabled(profile.notifications_enabled ?? true);
    }
  }, [profileData]);

  // Update profile mutation
  const updateMutation = useMutation({
    mutationFn: (settings: Parameters<typeof onboardingService.updateProfile>[0]) =>
      onboardingService.updateProfile(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      hapticFeedback('success');
    },
  });

  const toggleDay = (dayId: number) => {
    const newDays = workDays.includes(dayId)
      ? workDays.filter((d) => d !== dayId)
      : [...workDays, dayId].sort();
    setWorkDays(newDays);
    updateMutation.mutate({ work_days: newDays });
  };

  const handleWorkStartChange = (time: string) => {
    setWorkStartTime(time);
    updateMutation.mutate({ work_start_time: time });
  };

  const handleWorkEndChange = (time: string) => {
    setWorkEndTime(time);
    updateMutation.mutate({ work_end_time: time });
  };

  const handleSessionDurationChange = (duration: number) => {
    setSessionDuration(duration);
    updateMutation.mutate({ preferred_session_duration: duration });
  };

  const handleReminderTimeChange = (time: string) => {
    setReminderTime(time);
    updateMutation.mutate({ daily_reminder_time: time });
  };

  const handleNotificationsToggle = () => {
    const newValue = !notificationsEnabled;
    setNotificationsEnabled(newValue);
    updateMutation.mutate({ notifications_enabled: newValue });
  };

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        <Card className="h-24 animate-pulse" />
        <Card className="h-32 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <ScrollBackdrop />
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/profile')}
          className="p-2 -ml-2 hover:bg-gray-700 rounded-full"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <h1 className="text-xl font-bold text-white">Настройки</h1>
      </div>

      {/* Work Schedule */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-primary-500" />
          <h2 className="font-semibold text-white">Рабочее расписание</h2>
        </div>

        {/* Work Days */}
        <div className="mb-4">
          <p className="text-sm text-gray-400 mb-2">Рабочие дни</p>
          <div className="flex gap-1">
            {DAYS_OF_WEEK.map((day) => (
              <button
                key={day.id}
                onClick={() => toggleDay(day.id)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                  workDays.includes(day.id)
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {day.short}
              </button>
            ))}
          </div>
        </div>

        {/* Work Hours */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-sm text-gray-400 mb-1">Начало работы</p>
            <input
              type="time"
              value={workStartTime}
              onChange={(e) => handleWorkStartChange(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-1">Конец работы</p>
            <input
              type="time"
              value={workEndTime}
              onChange={(e) => handleWorkEndChange(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>
      </Card>

      {/* Focus Settings */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Timer className="w-5 h-5 text-accent-500" />
          <h2 className="font-semibold text-white">Фокус-сессии</h2>
        </div>

        <p className="text-sm text-gray-400 mb-2">Длительность по умолчанию</p>
        <div className="flex gap-2">
          {SESSION_DURATIONS.map((d) => (
            <button
              key={d}
              onClick={() => handleSessionDurationChange(d)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                sessionDuration === d
                  ? 'bg-accent-500 text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              {d} мин
            </button>
          ))}
        </div>
      </Card>

      {/* Notifications */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5 text-yellow-500" />
          <h2 className="font-semibold text-white">Уведомления</h2>
        </div>

        <div className="flex items-center justify-between mb-3">
          <span className="text-gray-300">Включить уведомления</span>
          <button
            onClick={handleNotificationsToggle}
            className={`w-12 h-6 rounded-full transition-colors ${
              notificationsEnabled ? 'bg-primary-500' : 'bg-gray-600'
            }`}
          >
            <div
              className={`w-5 h-5 bg-white rounded-full transition-transform ${
                notificationsEnabled ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {notificationsEnabled && (
          <div>
            <p className="text-sm text-gray-400 mb-1">Время напоминания</p>
            <input
              type="time"
              value={reminderTime}
              onChange={(e) => handleReminderTimeChange(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        )}
      </Card>

      {/* Language */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Globe className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold text-white">{t('language')}</h2>
        </div>

        <div className="flex gap-2">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.id}
              onClick={() => {
                setLanguage(lang.id);
                // Invalidate all cached queries to refetch with new language
                queryClient.invalidateQueries();
                hapticFeedback('light');
              }}
              className={`flex-1 py-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                language === lang.id
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              <span className="text-lg">{lang.flag}</span>
              <span>{lang.label}</span>
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}
