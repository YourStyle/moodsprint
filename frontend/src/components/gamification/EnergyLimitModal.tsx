'use client';

import { useState, useEffect } from 'react';
import { Zap } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { useTranslation } from '@/lib/i18n';

interface EnergyLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  oldMax: number;
  newMax: number;
}

export function EnergyLimitModal({ isOpen, onClose, oldMax, newMax }: EnergyLimitModalProps) {
  const { t } = useTranslation();
  const [displayValue, setDisplayValue] = useState(oldMax);

  // Animate counter from oldMax to newMax
  useEffect(() => {
    if (!isOpen) {
      setDisplayValue(oldMax);
      return;
    }

    // Start animation after a brief delay
    const startDelay = setTimeout(() => {
      const step = newMax > oldMax ? 1 : -1;
      const interval = setInterval(() => {
        setDisplayValue((prev) => {
          const next = prev + step;
          if ((step > 0 && next >= newMax) || (step < 0 && next <= newMax)) {
            clearInterval(interval);
            return newMax;
          }
          return next;
        });
      }, 200);

      return () => clearInterval(interval);
    }, 500);

    return () => clearTimeout(startDelay);
  }, [isOpen, oldMax, newMax]);

  const increase = newMax - oldMax;
  const progress = newMax > oldMax
    ? ((displayValue - oldMax) / (newMax - oldMax)) * 100
    : 100;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('energyLimitIncreased')}>
      <div className="flex flex-col items-center py-2">
        {/* Animated energy icon */}
        <div className="relative mb-6">
          <div className="absolute inset-0 blur-2xl bg-cyan-500/30 rounded-full animate-pulse" />
          <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/40">
            <Zap className="w-10 h-10 text-white fill-white" />
          </div>
        </div>

        {/* Animated counter */}
        <div className="text-4xl font-bold text-cyan-400 mb-2 tabular-nums">
          ⚡ {displayValue}
        </div>

        {/* Progress bar */}
        <div className="w-full max-w-[200px] h-3 bg-gray-700 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(100, progress)}%` }}
          />
        </div>

        {/* Old → New display */}
        <div className="flex items-center gap-4 mb-3 text-sm">
          <span className="text-gray-500">
            {t('energyLimitFrom').replace('{old}', String(oldMax))}
          </span>
          <span className="text-cyan-400 font-medium">→</span>
          <span className="text-cyan-400 font-medium">
            {t('energyLimitTo').replace('{new}', String(newMax))}
          </span>
        </div>

        {/* +N indicator */}
        <div className="bg-cyan-500/20 px-4 py-1.5 rounded-full mb-4">
          <span className="text-cyan-400 font-bold">+{increase} ⚡</span>
        </div>

        {/* Explanation */}
        <p className="text-sm text-gray-400 text-center mb-5">
          {t('energyLimitExplain')}
        </p>

        {/* Close button */}
        <Button onClick={onClose} className="w-full">
          {t('great')}
        </Button>
      </div>
    </Modal>
  );
}
