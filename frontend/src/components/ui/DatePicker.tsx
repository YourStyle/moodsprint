'use client';

import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import { useLanguage } from '@/lib/i18n';

interface DatePickerProps {
  value: string; // "YYYY-MM-DD"
  onChange: (value: string) => void;
  min?: string; // "YYYY-MM-DD"
  className?: string;
  /** Show the trigger as just an icon button (for inline use) */
  compact?: boolean;
}

const MONTH_NAMES_RU = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
];
const MONTH_NAMES_EN = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const WEEKDAYS_RU = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const WEEKDAYS_EN = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function toDateStr(y: number, m: number, d: number): string {
  return `${y}-${pad(m + 1)}-${pad(d)}`;
}

function parseDate(s: string): { year: number; month: number; day: number } {
  const [y, m, d] = s.split('-').map(Number);
  return { year: y, month: m - 1, day: d };
}

export function DatePicker({ value, onChange, min, className, compact }: DatePickerProps) {
  const { language } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const parsed = parseDate(value || new Date().toISOString().split('T')[0]);
  const [viewYear, setViewYear] = useState(parsed.year);
  const [viewMonth, setViewMonth] = useState(parsed.month);

  // Sync view when value changes externally
  useEffect(() => {
    const p = parseDate(value || new Date().toISOString().split('T')[0]);
    setViewYear(p.year);
    setViewMonth(p.month);
  }, [value]);

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

  const monthNames = language === 'ru' ? MONTH_NAMES_RU : MONTH_NAMES_EN;
  const weekdays = language === 'ru' ? WEEKDAYS_RU : WEEKDAYS_EN;

  const minDate = min ? parseDate(min) : null;

  const isDisabled = useCallback((y: number, m: number, d: number): boolean => {
    if (!minDate) return false;
    const dateStr = toDateStr(y, m, d);
    const minStr = min!;
    return dateStr < minStr;
  }, [min, minDate]);

  // Build calendar grid
  const calendarDays = useMemo(() => {
    const firstDay = new Date(viewYear, viewMonth, 1);
    const lastDay = new Date(viewYear, viewMonth + 1, 0);
    const daysInMonth = lastDay.getDate();

    // Monday = 0, Sunday = 6 for our grid
    let startWeekday = firstDay.getDay() - 1;
    if (startWeekday < 0) startWeekday = 6;

    const days: Array<{ day: number; month: number; year: number; isCurrentMonth: boolean }> = [];

    // Previous month padding
    const prevMonthLastDay = new Date(viewYear, viewMonth, 0).getDate();
    for (let i = startWeekday - 1; i >= 0; i--) {
      const pMonth = viewMonth === 0 ? 11 : viewMonth - 1;
      const pYear = viewMonth === 0 ? viewYear - 1 : viewYear;
      days.push({ day: prevMonthLastDay - i, month: pMonth, year: pYear, isCurrentMonth: false });
    }

    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
      days.push({ day: d, month: viewMonth, year: viewYear, isCurrentMonth: true });
    }

    // Next month padding (fill to complete rows)
    const remaining = 7 - (days.length % 7);
    if (remaining < 7) {
      const nMonth = viewMonth === 11 ? 0 : viewMonth + 1;
      const nYear = viewMonth === 11 ? viewYear + 1 : viewYear;
      for (let d = 1; d <= remaining; d++) {
        days.push({ day: d, month: nMonth, year: nYear, isCurrentMonth: false });
      }
    }

    return days;
  }, [viewYear, viewMonth]);

  const prevMonth = () => {
    if (viewMonth === 0) { setViewYear(viewYear - 1); setViewMonth(11); }
    else setViewMonth(viewMonth - 1);
  };

  const nextMonth = () => {
    if (viewMonth === 11) { setViewYear(viewYear + 1); setViewMonth(0); }
    else setViewMonth(viewMonth + 1);
  };

  const selectDate = (y: number, m: number, d: number) => {
    if (isDisabled(y, m, d)) return;
    onChange(toDateStr(y, m, d));
    setIsOpen(false);
  };

  const todayStr = new Date().toISOString().split('T')[0];

  const displayValue = useMemo(() => {
    const d = new Date(value + 'T00:00:00');
    const locale = language === 'ru' ? 'ru-RU' : 'en-US';
    return d.toLocaleDateString(locale, { day: 'numeric', month: 'short' });
  }, [value, language]);

  return (
    <div ref={containerRef} className={`relative ${className || ''}`}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={compact
          ? 'flex items-center gap-1.5 text-sm font-medium text-gray-300 hover:text-white transition-colors'
          : 'w-full flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-700 border border-gray-600 text-white text-sm hover:border-gray-500 transition-colors focus:ring-2 focus:ring-primary-500 focus:border-transparent'
        }
      >
        <Calendar className="w-4 h-4 text-gray-400" />
        <span>{displayValue}</span>
      </button>

      {/* Calendar dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-1 left-0 bg-gray-800 border border-gray-600 rounded-xl shadow-xl p-3 w-[280px]">
          {/* Header with month/year navigation */}
          <div className="flex items-center justify-between mb-3">
            <button
              type="button"
              onClick={prevMonth}
              className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium text-white">
              {monthNames[viewMonth]} {viewYear}
            </span>
            <button
              type="button"
              onClick={nextMonth}
              className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 mb-1">
            {weekdays.map((wd) => (
              <div key={wd} className="text-center text-[10px] font-medium text-gray-500 py-1">
                {wd}
              </div>
            ))}
          </div>

          {/* Days grid */}
          <div className="grid grid-cols-7">
            {calendarDays.map((cell, idx) => {
              const dateStr = toDateStr(cell.year, cell.month, cell.day);
              const isSelected = dateStr === value;
              const isToday = dateStr === todayStr;
              const disabled = isDisabled(cell.year, cell.month, cell.day);

              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => selectDate(cell.year, cell.month, cell.day)}
                  disabled={disabled}
                  className={`
                    h-9 w-full rounded-lg text-xs font-medium transition-all
                    ${!cell.isCurrentMonth ? 'text-gray-600' : ''}
                    ${cell.isCurrentMonth && !isSelected && !disabled ? 'text-gray-200 hover:bg-gray-700' : ''}
                    ${isSelected ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30' : ''}
                    ${isToday && !isSelected ? 'ring-1 ring-primary-500/50 text-primary-400' : ''}
                    ${disabled ? 'text-gray-700 cursor-not-allowed' : ''}
                  `}
                >
                  {cell.day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
