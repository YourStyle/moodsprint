'use client';

import { useQuery } from '@tanstack/react-query';
import { Sparkles, ChevronRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui';
import { sparksService } from '@/services/sparks';
import { useAppStore } from '@/lib/store';

interface SparksBalanceProps {
  showBuyButton?: boolean;
  compact?: boolean;
}

export function SparksBalance({ showBuyButton = true, compact = false }: SparksBalanceProps) {
  const router = useRouter();
  const { user } = useAppStore();

  const { data } = useQuery({
    queryKey: ['sparks', 'balance'],
    queryFn: () => sparksService.getBalance(),
    enabled: !!user,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const sparks = data?.data?.sparks ?? user?.sparks ?? 0;

  if (compact) {
    return (
      <button
        onClick={() => router.push('/store')}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border border-amber-500/30 hover:border-amber-400/50 transition-colors"
      >
        <Sparkles className="w-4 h-4 text-amber-400" />
        <span className="font-semibold text-amber-400">{sparks.toLocaleString()}</span>
      </button>
    );
  }

  return (
    <Card className="bg-gradient-to-br from-amber-500/10 to-yellow-500/10 border-amber-500/20">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <p className="text-sm text-gray-400">Sparks</p>
            <p className="text-2xl font-bold text-amber-400">{sparks.toLocaleString()}</p>
          </div>
        </div>
        {showBuyButton && (
          <button
            onClick={() => router.push('/store')}
            className="flex items-center gap-1 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-600 to-yellow-600 text-white font-medium hover:from-amber-500 hover:to-yellow-500 transition-colors"
          >
            <span>Купить</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </Card>
  );
}
