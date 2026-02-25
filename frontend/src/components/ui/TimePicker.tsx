'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Clock } from 'lucide-react';

interface TimePickerProps {
  value: string; // "HH:MM"
  onChange: (value: string) => void;
  className?: string;
}

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = Array.from({ length: 12 }, (_, i) => i * 5);

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

/** Round a time string to the nearest 5 minutes. */
export function roundToFiveMinutes(time: string): string {
  const [h, m] = time.split(':').map(Number);
  const rounded = Math.round(m / 5) * 5;
  if (rounded === 60) return `${pad(h === 23 ? 0 : h + 1)}:00`;
  return `${pad(h)}:${pad(rounded)}`;
}

export function TimePicker({ value, onChange, className }: TimePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const hoursRef = useRef<HTMLDivElement>(null);
  const minutesRef = useRef<HTMLDivElement>(null);

  const [h, m] = (value || '12:00').split(':').map(Number);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  // Auto-scroll to selected value on open
  useEffect(() => {
    if (!isOpen) return;
    requestAnimationFrame(() => {
      const scrollToSelected = (container: HTMLDivElement | null, index: number) => {
        if (!container) return;
        const item = container.children[index] as HTMLElement;
        if (item) {
          item.scrollIntoView({ block: 'center', behavior: 'auto' });
        }
      };
      scrollToSelected(hoursRef.current, h);
      scrollToSelected(minutesRef.current, Math.round(m / 5));
    });
  }, [isOpen, h, m]);

  const selectHour = useCallback((hour: number) => {
    onChange(`${pad(hour)}:${pad(m)}`);
  }, [m, onChange]);

  const selectMinute = useCallback((minute: number) => {
    onChange(`${pad(h)}:${pad(minute)}`);
    // Close after minute selection for quick use
    setTimeout(() => setIsOpen(false), 150);
  }, [h, onChange]);

  return (
    <div ref={containerRef} className={`relative ${className || ''}`}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-700 border border-gray-600 text-white text-sm hover:border-gray-500 transition-colors focus:ring-2 focus:ring-primary-500 focus:border-transparent"
      >
        <Clock className="w-4 h-4 text-gray-400" />
        <span>{pad(h)}:{pad(m)}</span>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-1 left-0 right-0 bg-gray-800 border border-gray-600 rounded-xl shadow-xl overflow-hidden">
          <div className="flex divide-x divide-gray-700">
            {/* Hours column */}
            <div
              ref={hoursRef}
              className="flex-1 h-48 overflow-y-auto scrollbar-thin"
            >
              {HOURS.map((hour) => (
                <button
                  key={hour}
                  type="button"
                  onClick={() => selectHour(hour)}
                  className={`w-full py-2 text-center text-sm transition-colors ${
                    hour === h
                      ? 'bg-primary-500/20 text-primary-400 font-medium'
                      : 'text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {pad(hour)}
                </button>
              ))}
            </div>
            {/* Minutes column */}
            <div
              ref={minutesRef}
              className="flex-1 h-48 overflow-y-auto scrollbar-thin"
            >
              {MINUTES.map((minute) => (
                <button
                  key={minute}
                  type="button"
                  onClick={() => selectMinute(minute)}
                  className={`w-full py-2 text-center text-sm transition-colors ${
                    minute === m
                      ? 'bg-primary-500/20 text-primary-400 font-medium'
                      : 'text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {pad(minute)}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
