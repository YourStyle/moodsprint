'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { eventsService } from '@/services/events';
import { useLanguage } from '@/lib/i18n';

export function EventBanner() {
  const router = useRouter();
  const { t } = useLanguage();

  const { data: eventData } = useQuery({
    queryKey: ['activeEvent'],
    queryFn: () => eventsService.getActiveEvent(),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const event = eventData?.data?.event;
  if (!event || !event.is_currently_active) return null;

  const themeColor = event.theme_color || '#FF6B00';

  return (
    <button
      onClick={() => router.push('/arena')}
      className="w-full rounded-xl p-3 flex items-center gap-3 transition-transform active:scale-[0.98]"
      style={{
        background: `linear-gradient(135deg, ${themeColor}20, ${themeColor}10)`,
        border: `1px solid ${themeColor}40`,
      }}
    >
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0"
        style={{ background: `${themeColor}30` }}
      >
        {event.emoji}
      </div>
      <div className="flex-1 min-w-0 text-left">
        <p className="text-sm font-semibold text-white truncate">
          {event.name}
        </p>
        <p className="text-xs text-white/60 truncate">
          {event.xp_multiplier > 1
            ? `XP x${event.xp_multiplier} · `
            : ''}
          {event.days_remaining > 0
            ? `${event.days_remaining}${t('daysLeft')}`
            : t('lastDay')}
        </p>
      </div>
      <div
        className="text-xs font-medium px-2 py-1 rounded-full flex-shrink-0"
        style={{
          background: `${themeColor}30`,
          color: themeColor,
        }}
      >
        {t('event')}
      </div>
    </button>
  );
}
