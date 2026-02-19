'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { formatDateForAPI } from '@/lib/dateUtils';
import { hapticFeedback } from '@/lib/telegram';

export interface WeekCalendarProps {
  selectedDate: Date;
  onDateSelect: (date: Date) => void;
  language: 'ru' | 'en';
  taskCounts?: Record<string, number>;
}

const WEEK_DAYS = {
  ru: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
  en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
};

const MONTH_NAMES = {
  ru: ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
};

/**
 * Horizontal scrollable week calendar with date selection and per-day task count badges.
 *
 * Usage:
 *   <WeekCalendar
 *     selectedDate={selectedDate}
 *     onDateSelect={setSelectedDate}
 *     language={language}
 *     taskCounts={taskCounts}
 *   />
 */
export function WeekCalendar({
  selectedDate,
  onDateSelect,
  language,
  taskCounts = {},
}: WeekCalendarProps) {
  const days = WEEK_DAYS[language];
  const months = MONTH_NAMES[language];
  const today = new Date();
  const selectedDateStr = formatDateForAPI(selectedDate);
  const todayStr = formatDateForAPI(today);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showLeftArrow, setShowLeftArrow] = useState(false);
  const [showRightArrow, setShowRightArrow] = useState(true);

  // Generate 38 days: 7 days back + today + 30 days forward
  const allDays = useMemo(() => {
    const result: Date[] = [];
    for (let i = -7; i <= 30; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      result.push(date);
    }
    return result;
  }, []);

  // Find index of selected date in allDays array
  const selectedIndex = useMemo(() => {
    const selectedStr = formatDateForAPI(selectedDate);
    return allDays.findIndex(d => formatDateForAPI(d) === selectedStr);
  }, [allDays, selectedDate]);

  // Default to today's index (7) if selected date not found
  const scrollToIndex = selectedIndex >= 0 ? selectedIndex : 7;

  // Update arrow visibility based on scroll position
  const updateArrowVisibility = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
    setShowLeftArrow(scrollLeft > 10);
    setShowRightArrow(scrollLeft < scrollWidth - clientWidth - 10);
  }, []);

  // Scroll by a fixed amount in a given direction
  const scrollBy = useCallback((direction: 'left' | 'right') => {
    if (!scrollRef.current) return;
    const scrollAmount = 200;
    scrollRef.current.scrollBy({
      left: direction === 'left' ? -scrollAmount : scrollAmount,
      behavior: 'smooth',
    });
  }, []);

  // Initial scroll to selected date (or today if not found)
  useEffect(() => {
    if (scrollRef.current && !scrollRef.current.dataset.scrolled) {
      const container = scrollRef.current.querySelector('.flex.gap-1');
      if (container) {
        const targetElement = container.children[scrollToIndex] as HTMLElement;
        if (targetElement) {
          const scrollLeft =
            targetElement.offsetLeft -
            scrollRef.current.clientWidth / 2 +
            targetElement.clientWidth / 2;
          scrollRef.current.scrollLeft = Math.max(0, scrollLeft);
          scrollRef.current.dataset.scrolled = 'true';
          updateArrowVisibility();
        }
      }
    }
  }, [scrollToIndex, updateArrowVisibility]);

  return (
    <div className="flex items-center gap-1 pt-4">
      {/* Left arrow */}
      <button
        onClick={() => scrollBy('left')}
        disabled={!showLeftArrow}
        className={`flex-shrink-0 w-8 h-16 flex items-center justify-center transition-opacity ${
          showLeftArrow ? 'opacity-100' : 'opacity-30'
        }`}
      >
        <ChevronLeft className="w-5 h-5 text-gray-400" />
      </button>

      {/* Scrollable dates */}
      <div
        ref={scrollRef}
        onScroll={updateArrowVisibility}
        className="flex-1 overflow-x-auto pb-1 overflow-y-visible"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        <div className="flex gap-1">
          {allDays.map((date, index) => {
            const dateStr = formatDateForAPI(date);
            const isSelected = dateStr === selectedDateStr;
            const isToday = dateStr === todayStr;
            const taskCount = taskCounts[dateStr] || 0;
            const dayOfWeek = days[date.getDay()];
            const isPast = date < today && !isToday;
            const isNewMonth = date.getDate() === 1 || index === 0;

            return (
              <button
                key={dateStr}
                onClick={() => {
                  hapticFeedback('light');
                  onDateSelect(date);
                }}
                className={`relative flex flex-col items-center py-2 px-3 rounded-xl transition-all flex-shrink-0 min-w-[52px] mt-2 ${
                  isSelected
                    ? 'bg-primary-500/20 border border-primary-500/50'
                    : isToday
                    ? 'bg-dark-600 border border-gray-700'
                    : isPast
                    ? 'opacity-40 hover:opacity-60'
                    : 'opacity-70 hover:opacity-100'
                }`}
              >
                <span className="text-[10px] text-gray-400 mb-0.5">{dayOfWeek}</span>
                <span
                  className={`text-lg font-semibold ${
                    isSelected ? 'text-primary-400' : isToday ? 'text-white' : 'text-gray-400'
                  }`}
                >
                  {date.getDate()}
                </span>
                {isNewMonth && (
                  <span className="text-[9px] text-gray-500">{months[date.getMonth()]}</span>
                )}
                {taskCount > 0 && !isSelected && (
                  <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-purple-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center">
                    {taskCount > 9 ? '9+' : taskCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Right arrow */}
      <button
        onClick={() => scrollBy('right')}
        disabled={!showRightArrow}
        className={`flex-shrink-0 w-8 h-16 flex items-center justify-center transition-opacity ${
          showRightArrow ? 'opacity-100' : 'opacity-30'
        }`}
      >
        <ChevronRight className="w-5 h-5 text-gray-400" />
      </button>

      <style jsx>{`
        div::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}
