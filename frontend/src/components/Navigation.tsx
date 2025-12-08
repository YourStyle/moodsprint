'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, ListTodo, Timer, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';

const navItems = [
  { href: '/', icon: Home, label: 'Главная' },
  { href: '/tasks', icon: ListTodo, label: 'Задачи' },
  { href: '/focus', icon: Timer, label: 'Фокус' },
  { href: '/profile', icon: User, label: 'Профиль' },
];

export function Navigation() {
  const pathname = usePathname();
  const { activeSession } = useAppStore();

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 pb-4 safe-area-bottom">
      <div className="max-w-md mx-auto px-4">
        <nav className="flex items-center justify-center">
          <div
            className="relative rounded-full px-6 py-3 flex items-center justify-center gap-2 overflow-hidden"
            style={{
              background: 'rgba(17, 24, 39, 0.85)',
              backdropFilter: 'blur(20px) saturate(180%)',
              WebkitBackdropFilter: 'blur(20px) saturate(180%)',
              boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 1px 0 0 rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
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
              const showBadge = item.href === '/focus' && activeSession;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex flex-col items-center gap-1 transition-colors relative group min-w-[60px] z-10',
                    isActive ? 'text-white' : 'text-gray-400 hover:text-gray-300'
                  )}
                >
                  <div className="relative">
                    <Icon
                      className={cn(
                        'transition-all duration-200 w-6 h-6',
                        isActive && 'scale-110'
                      )}
                    />
                    {showBadge && (
                      <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse" />
                    )}
                  </div>
                  <span className="text-xs font-medium">{item.label}</span>
                  {isActive && (
                    <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-purple-400 rounded-full" />
                  )}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}
