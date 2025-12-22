'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ListTodo, Users, User, Swords, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { useLanguage, TranslationKey } from '@/lib/i18n';
import { cardsService } from '@/services';

const navItems: { href: string; icon: typeof ListTodo; labelKey: TranslationKey }[] = [
  { href: '/', icon: ListTodo, labelKey: 'tasks' },
  { href: '/friends', icon: Users, labelKey: 'friends' },
  { href: '/deck', icon: Layers, labelKey: 'deck' },
  { href: '/arena', icon: Swords, labelKey: 'arena' },
  { href: '/profile', icon: User, labelKey: 'profile' },
];

export function Navigation() {
  const pathname = usePathname();
  const { activeSession, user } = useAppStore();
  const { t } = useLanguage();

  // Fetch pending friend requests count
  const { data: friendRequestsData } = useQuery({
    queryKey: ['friends', 'requests'],
    queryFn: () => cardsService.getFriendRequests(),
    enabled: !!user,
    staleTime: 1000 * 60 * 2, // 2 minutes
    refetchInterval: 1000 * 60 * 2, // Refetch every 2 minutes
  });

  const pendingRequestsCount = friendRequestsData?.data?.total || 0;

  // Hide navigation on onboarding page
  if (pathname === '/onboarding') {
    return null;
  }

  return (
    <motion.div
      className="fixed bottom-1.5 left-0 right-0 z-50 pb-4 safe-area-bottom"
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      <div className="max-w-md mx-auto px-4">
        <nav className="flex items-center justify-center">
          <motion.div
            className="relative rounded-full px-6 py-3 flex items-center justify-center gap-2 overflow-hidden"
            style={{
              background: 'rgba(17, 24, 39, 0.85)',
              backdropFilter: 'blur(20px) saturate(180%)',
              WebkitBackdropFilter: 'blur(20px) saturate(180%)',
              boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 1px 0 0 rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
            whileHover={{ scale: 1.02 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          >
            {/* Gradient overlay */}
            <div
              className="absolute inset-0 rounded-full pointer-events-none"
              style={{
                background: 'radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.15) 0%, transparent 50%)',
              }}
            />
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              const showFocusBadge = item.href === '/focus' && activeSession;
              const showFriendsBadge = item.href === '/friends' && pendingRequestsCount > 0;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex flex-col items-center gap-1 relative group min-w-[60px] z-10',
                    isActive ? 'text-white' : 'text-gray-400 hover:text-gray-300'
                  )}
                  data-onboarding={item.href === '/deck' ? 'nav-deck' : undefined}
                >
                  <motion.div
                    className="relative"
                    whileTap={{ scale: 0.9 }}
                    animate={{ scale: isActive ? 1.1 : 1 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 17 }}
                  >
                    <Icon className="w-6 h-6" />
                    <AnimatePresence>
                      {showFocusBadge && (
                        <motion.span
                          className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-green-500 rounded-full"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          exit={{ scale: 0 }}
                        />
                      )}
                      {showFriendsBadge && (
                        <motion.span
                          className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          exit={{ scale: 0 }}
                        >
                          {pendingRequestsCount > 9 ? '9+' : pendingRequestsCount}
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </motion.div>
                  <span className="text-xs font-medium">{t(item.labelKey)}</span>
                  <AnimatePresence>
                    {isActive && (
                      <motion.div
                        className="absolute -bottom-1 left-1/2 w-1 h-1 bg-purple-400 rounded-full"
                        layoutId="activeIndicator"
                        initial={{ opacity: 0, x: '-50%' }}
                        animate={{ opacity: 1, x: '-50%' }}
                        exit={{ opacity: 0 }}
                        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                      />
                    )}
                  </AnimatePresence>
                </Link>
              );
            })}
          </motion.div>
        </nav>
      </div>
    </motion.div>
  );
}
