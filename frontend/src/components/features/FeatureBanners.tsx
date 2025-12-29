'use client';

import { useRouter } from 'next/navigation';
import { Shield, Store, Map, ChevronRight, Sparkles, Swords, Trophy, Gift } from 'lucide-react';
import { hapticFeedback } from '@/lib/telegram';
import { cn } from '@/lib/utils';

interface FeatureBannerProps {
  type: 'guilds' | 'marketplace' | 'campaign';
  stats?: {
    guilds?: { memberCount?: number; hasGuild?: boolean };
    marketplace?: { balance?: number; listingsCount?: number };
    campaign?: { currentChapter?: number; starsEarned?: number };
  };
}

const FEATURE_CONFIG = {
  guilds: {
    icon: Shield,
    title: 'Гильдии',
    description: 'Объединяйся с друзьями, побеждай боссов в рейдах',
    href: '/guilds',
    gradient: 'from-blue-600/30 via-indigo-600/30 to-purple-600/30',
    borderColor: 'border-blue-500/40',
    iconBg: 'bg-blue-500/30',
    iconColor: 'text-blue-400',
    buttonGradient: 'from-blue-600 to-indigo-600',
    highlights: [
      { icon: Swords, text: 'Рейды' },
      { icon: Trophy, text: 'Награды' },
    ],
  },
  marketplace: {
    icon: Store,
    title: 'Маркетплейс',
    description: 'Торгуй картами за Telegram Stars',
    href: '/marketplace',
    gradient: 'from-amber-600/30 via-orange-600/30 to-yellow-600/30',
    borderColor: 'border-amber-500/40',
    iconBg: 'bg-amber-500/30',
    iconColor: 'text-amber-400',
    buttonGradient: 'from-amber-600 to-orange-600',
    highlights: [
      { icon: Store, text: 'Карты' },
      { icon: Gift, text: 'Продажа' },
    ],
  },
  campaign: {
    icon: Map,
    title: 'Кампания',
    description: 'Проходи главы, побеждай боссов, собирай награды',
    href: '/campaign',
    gradient: 'from-purple-600/30 via-fuchsia-600/30 to-pink-600/30',
    borderColor: 'border-purple-500/40',
    iconBg: 'bg-purple-500/30',
    iconColor: 'text-purple-400',
    buttonGradient: 'from-purple-600 to-fuchsia-600',
    highlights: [
      { icon: Map, text: 'История' },
      { icon: Sparkles, text: 'Лор' },
    ],
  },
};

export function FeatureBanner({ type, stats }: FeatureBannerProps) {
  const router = useRouter();
  const config = FEATURE_CONFIG[type];
  const Icon = config.icon;

  const handleClick = () => {
    hapticFeedback('light');
    router.push(config.href);
  };

  const getStatText = () => {
    if (type === 'guilds' && stats?.guilds) {
      if (stats.guilds.hasGuild) {
        return `${stats.guilds.memberCount || 0} участников`;
      }
      return 'Присоединяйся!';
    }
    if (type === 'marketplace' && stats?.marketplace) {
      return `${stats.marketplace.listingsCount || 0} карт на продаже`;
    }
    if (type === 'campaign' && stats?.campaign) {
      return `Глава ${stats.campaign.currentChapter || 1} • ${stats.campaign.starsEarned || 0} ⭐`;
    }
    return null;
  };

  const statText = getStatText();

  return (
    <div
      onClick={handleClick}
      className={cn(
        'relative overflow-hidden rounded-2xl p-4 cursor-pointer transition-all active:scale-[0.98]',
        `bg-gradient-to-r ${config.gradient}`,
        'border',
        config.borderColor
      )}
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 -translate-y-8 translate-x-8 opacity-20">
        <Icon className="w-full h-full" />
      </div>

      <div className="relative flex items-center gap-4">
        {/* Icon */}
        <div className={cn(
          'w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0',
          config.iconBg
        )}>
          <Icon className={cn('w-7 h-7', config.iconColor)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-bold text-white mb-0.5">{config.title}</h3>
          <p className="text-sm text-gray-300 line-clamp-1">{config.description}</p>

          {/* Highlights */}
          <div className="flex items-center gap-3 mt-2">
            {config.highlights.map((h, i) => (
              <div key={i} className="flex items-center gap-1 text-xs text-gray-400">
                <h.icon className="w-3 h-3" />
                <span>{h.text}</span>
              </div>
            ))}
            {statText && (
              <span className={cn('text-xs font-medium', config.iconColor)}>
                {statText}
              </span>
            )}
          </div>
        </div>

        {/* Arrow */}
        <div className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          `bg-gradient-to-r ${config.buttonGradient}`
        )}>
          <ChevronRight className="w-5 h-5 text-white" />
        </div>
      </div>
    </div>
  );
}

// Combined banners section for deck page
export function FeatureBannersSection({
  guildStats,
  marketplaceStats,
  campaignStats
}: {
  guildStats?: { memberCount?: number; hasGuild?: boolean };
  marketplaceStats?: { balance?: number; listingsCount?: number };
  campaignStats?: { currentChapter?: number; starsEarned?: number };
}) {
  return (
    <div className="space-y-3">
      <FeatureBanner
        type="campaign"
        stats={{ campaign: campaignStats }}
      />
      <FeatureBanner
        type="guilds"
        stats={{ guilds: guildStats }}
      />
      <FeatureBanner
        type="marketplace"
        stats={{ marketplace: marketplaceStats }}
      />
    </div>
  );
}
