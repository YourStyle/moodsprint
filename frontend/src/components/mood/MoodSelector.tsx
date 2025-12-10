'use client';

import { useState } from 'react';
import clsx from 'clsx';
import { Button } from '@/components/ui';
import { MOOD_EMOJIS, MOOD_LABELS, ENERGY_EMOJIS, ENERGY_LABELS } from '@/domain/constants';
import type { MoodLevel, EnergyLevel } from '@/domain/types';

interface MoodSelectorProps {
  onSubmit: (mood: MoodLevel, energy: EnergyLevel, note?: string) => void;
  isLoading?: boolean;
}

export function MoodSelector({ onSubmit, isLoading }: MoodSelectorProps) {
  const [mood, setMood] = useState<MoodLevel | null>(null);
  const [energy, setEnergy] = useState<EnergyLevel | null>(null);
  const [note, setNote] = useState('');
  const [step, setStep] = useState<'mood' | 'energy' | 'note'>('mood');

  const levels = [1, 2, 3, 4, 5] as const;

  const handleSubmit = () => {
    if (mood && energy) {
      onSubmit(mood, energy, note || undefined);
    }
  };

  const handleMoodSelect = (value: MoodLevel) => {
    setMood(value);
    setStep('energy');
  };

  const handleEnergySelect = (value: EnergyLevel) => {
    setEnergy(value);
    setStep('note');
  };

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
                  energy === level
                    ? 'bg-accent-100 ring-2 ring-accent-500'
                    : 'bg-gray-100 hover:bg-gray-200'
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

      {step === 'note' && (
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900">Заметки?</h3>
            <p className="text-sm text-gray-500 mt-1">
              {MOOD_EMOJIS[mood!]} {MOOD_LABELS[mood!]} | {ENERGY_EMOJIS[energy!]} {ENERGY_LABELS[energy!]}
            </p>
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Необязательно: что у тебя на уме?"
            className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/20 text-gray-900 placeholder:text-gray-400"
            rows={3}
            maxLength={500}
          />
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => setStep('energy')}
              className="flex-1"
            >
              Назад
            </Button>
            <Button
              onClick={handleSubmit}
              isLoading={isLoading}
              className="flex-1"
            >
              Сохранить
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
