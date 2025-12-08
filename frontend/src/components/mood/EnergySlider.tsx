'use client';

import { useState, useCallback } from 'react';
import clsx from 'clsx';

interface EnergySliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  className?: string;
}

export function EnergySlider({
  value,
  onChange,
  min = 1,
  max = 5,
  className,
}: EnergySliderProps) {
  const [isDragging, setIsDragging] = useState(false);

  const getEnergyLabel = (val: number) => {
    const labels = ['Низкая', 'Средняя', 'Высокая'];
    if (val <= 2) return labels[0];
    if (val <= 4) return labels[1];
    return labels[2];
  };

  const getEnergyColor = (val: number) => {
    if (val <= 2) return 'text-red-400';
    if (val <= 4) return 'text-yellow-400';
    return 'text-green-400';
  };

  const percent = ((value - min) / (max - min)) * 100;

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(parseInt(e.target.value, 10));
    },
    [onChange]
  );

  return (
    <div className={clsx('w-full', className)}>
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm text-gray-400">Низкая</span>
        <span className={clsx('text-sm font-medium', getEnergyColor(value))}>
          {getEnergyLabel(value)}
        </span>
        <span className="text-sm text-gray-400">Высокая</span>
      </div>

      <div className="relative h-3">
        {/* Track background with gradient */}
        <div className="absolute inset-0 rounded-full energy-gradient opacity-30" />

        {/* Filled track */}
        <div
          className="absolute left-0 top-0 h-full rounded-full energy-gradient transition-all"
          style={{ width: `${percent}%` }}
        />

        {/* Slider input */}
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={handleSliderChange}
          onMouseDown={() => setIsDragging(true)}
          onMouseUp={() => setIsDragging(false)}
          onTouchStart={() => setIsDragging(true)}
          onTouchEnd={() => setIsDragging(false)}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        />

        {/* Thumb */}
        <div
          className={clsx(
            'absolute top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-white shadow-lg shadow-purple-500/30 transition-transform pointer-events-none',
            isDragging && 'scale-110'
          )}
          style={{ left: `calc(${percent}% - 12px)` }}
        >
          <div className="absolute inset-1 rounded-full bg-gradient-to-br from-purple-500 to-purple-600" />
        </div>
      </div>

      {/* AI hint message */}
      {value <= 2 && (
        <div className="mt-4 glass-card p-3 animate-fade-in">
          <div className="flex items-start gap-2">
            <span className="text-lg">✨</span>
            <p className="text-sm text-gray-300">
              Низкая энергия! Предложу более лёгкие задачи на сегодня.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
