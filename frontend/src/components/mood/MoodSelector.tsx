'use client';

import { useState } from 'react';
import clsx from 'clsx';
import { MOOD_EMOJIS, MOOD_LABELS, ENERGY_EMOJIS } from '@/domain/constants';
import type { MoodLevel, EnergyLevel } from '@/domain/types';

interface MoodSelectorProps {
  onSubmit: (mood: MoodLevel, energy: EnergyLevel, note?: string) => void;
  isLoading?: boolean;
}

export function MoodSelector({ onSubmit, isLoading }: MoodSelectorProps) {
  const [mood, setMood] = useState<MoodLevel | null>(null);
  const [step, setStep] = useState<'mood' | 'energy'>('mood');

  const levels = [1, 2, 3, 4, 5] as const;

  const handleMoodSelect = (value: MoodLevel) => {
    setMood(value);
    setStep('energy');
  };

  const handleEnergySelect = (value: EnergyLevel) => {
    // Submit immediately after energy selection
    if (mood) {
      onSubmit(mood, value, undefined);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {step === 'mood' && (
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900">Как ты себя чувствуешь?</h3>
            <p className="text-sm text-gray-500 mt-1">Выбери своё настроение</p>
          </div>
          <div className="flex justify-center gap-2">
            {levels.map((level) => (
              <button
                key={level}
                onClick={() => handleMoodSelect(level)}
                className={clsx(
                  'w-14 h-14 rounded-2xl text-2xl transition-all',
                  'hover:scale-110 active:scale-95',
                  mood === level
                    ? 'bg-primary-100 ring-2 ring-primary-500'
                    : 'bg-gray-100 hover:bg-gray-200'
                )}
              >
                {MOOD_EMOJIS[level]}
              </button>
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-400 px-2">
            <span>Очень плохо</span>
            <span>Отлично</span>
          </div>
        </div>
      )}

      {step === 'energy' && (
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900">Уровень энергии?</h3>
            <p className="text-sm text-gray-500 mt-1">
              Настроение: {MOOD_EMOJIS[mood!]} {MOOD_LABELS[mood!]}
            </p>
          </div>
          <div className="flex justify-center gap-2">
            {levels.map((level) => (
              <button
                key={level}
                onClick={() => handleEnergySelect(level)}
                className={clsx(
                  'w-14 h-14 rounded-2xl text-2xl transition-all',
                  'hover:scale-110 active:scale-95',
                  'bg-gray-100 hover:bg-gray-200'
                )}
              >
                {ENERGY_EMOJIS[level]}
              </button>
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-400 px-2">
            <span>Истощён</span>
            <span>На пике</span>
          </div>
          <button
            onClick={() => setStep('mood')}
            className="text-sm text-gray-500 hover:text-gray-700 mx-auto block"
          >
            Назад к настроению
          </button>
        </div>
      )}
    </div>
  );
}
