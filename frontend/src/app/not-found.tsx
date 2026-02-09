'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { Home, ArrowLeft, Swords, ListTodo, Scroll, CheckCircle2 } from 'lucide-react';

const TRANSLATIONS = {
  ru: {
    title: 'Задача не найдена!',
    description: 'Кажется, эта карточка выпала из колоды и затерялась где-то в пространстве.',
    hint: 'Нажимай на карты, чтобы их перевернуть!',
    toTasks: 'К задачам',
    toHome: 'На главную',
    back: 'Назад',
    completedTasks: [
      'Выпить воды',
      'Размяться',
      'Проверить почту',
      'Сделать перерыв',
      'Позвонить маме',
      'Прочитать статью',
    ],
  },
  en: {
    title: 'Task not found!',
    description: 'Seems like this card fell out of the deck and got lost somewhere in space.',
    hint: 'Click on cards to flip them!',
    toTasks: 'To tasks',
    toHome: 'Home',
    back: 'Back',
    completedTasks: [
      'Drink water',
      'Stretch',
      'Check email',
      'Take a break',
      'Call mom',
      'Read an article',
    ],
  },
};

type Lang = 'ru' | 'en';

export default function NotFound() {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [lang, setLang] = useState<Lang>('ru');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [floatingCards, setFloatingCards] = useState<Array<{ id: number; x: number; y: number; rotation: number; delay: number; zone: 'left' | 'right' }>>([]);
  const [completedTasks, setCompletedTasks] = useState<Array<{ id: number; x: number; y: number; delay: number; zone: 'left' | 'right'; taskIndex: number }>>([]);

  const t = TRANSLATIONS[lang];

  // Detect language and auth status on mount
  useEffect(() => {
    // Check if user is logged in (has JWT token)
    const token = localStorage.getItem('moodsprint_token');
    setIsLoggedIn(!!token);

    // Check localStorage first (user preference)
    const storedLang = localStorage.getItem('moodsprint_language');
    if (storedLang === 'en' || storedLang === 'ru') {
      setLang(storedLang);
      return;
    }

    // Check browser language
    const browserLang = navigator.language.toLowerCase();
    if (browserLang.startsWith('ru')) {
      setLang('ru');
    } else {
      setLang('en');
    }
  }, []);

  // Generate floating elements on mount - cards on sides only
  useEffect(() => {
    // Cards - only on left and right sides, avoiding center
    const cards = [
      // Left side cards (x: 2-18%)
      { id: 0, x: 5, y: 15, rotation: -15, delay: 0, zone: 'left' as const },
      { id: 1, x: 12, y: 55, rotation: 10, delay: 1.5, zone: 'left' as const },
      { id: 2, x: 3, y: 75, rotation: -8, delay: 0.8, zone: 'left' as const },
      // Right side cards (x: 82-98%)
      { id: 3, x: 85, y: 20, rotation: 12, delay: 0.5, zone: 'right' as const },
      { id: 4, x: 92, y: 50, rotation: -10, delay: 2, zone: 'right' as const },
      { id: 5, x: 88, y: 80, rotation: 5, delay: 1.2, zone: 'right' as const },
    ];
    setFloatingCards(cards);

    // Completed task blocks - also on sides
    const tasks = [
      // Left side
      { id: 0, x: 8, y: 35, delay: 0.3, zone: 'left' as const, taskIndex: 0 },
      { id: 1, x: 2, y: 90, delay: 1.8, zone: 'left' as const, taskIndex: 1 },
      // Right side
      { id: 2, x: 82, y: 8, delay: 0.7, zone: 'right' as const, taskIndex: 2 },
      { id: 3, x: 90, y: 65, delay: 1.4, zone: 'right' as const, taskIndex: 3 },
    ];
    setCompletedTasks(tasks);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const handleCardClick = (id: number) => {
    setFloatingCards(prev => prev.map(card =>
      card.id === id ? { ...card, rotation: card.rotation + 360 } : card
    ));
  };

  return (
    <div className="fixed inset-0 z-50 bg-dark-900 flex flex-col items-center justify-center p-4 overflow-hidden">
      {/* Animated background gradient that follows mouse */}
      <div
        className="absolute w-96 h-96 rounded-full opacity-20 blur-3xl transition-all duration-300 pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(139,92,246,0.8) 0%, rgba(59,130,246,0.4) 50%, transparent 70%)',
          left: mousePos.x - 192,
          top: mousePos.y - 192,
        }}
      />

      {/* Floating cards decoration - positioned on sides */}
      {floatingCards.map((card) => (
        <div
          key={card.id}
          onClick={() => handleCardClick(card.id)}
          className="absolute cursor-pointer transition-all duration-500 hover:scale-110"
          style={{
            left: `${card.x}%`,
            top: `${card.y}%`,
            transform: `rotate(${card.rotation}deg)`,
            animation: `float ${4 + card.delay}s ease-in-out infinite`,
            animationDelay: `${card.delay}s`,
          }}
        >
          <div className="w-16 h-24 sm:w-20 sm:h-28 bg-gradient-to-br from-purple-600/40 to-blue-600/40 rounded-xl border-2 border-purple-500/40 backdrop-blur-sm flex items-center justify-center shadow-xl">
            <Scroll className="w-8 h-8 sm:w-10 sm:h-10 text-purple-400/70" />
          </div>
        </div>
      ))}

      {/* Floating completed task blocks */}
      {completedTasks.map((task) => (
        <div
          key={`task-${task.id}`}
          className="absolute pointer-events-none"
          style={{
            left: `${task.x}%`,
            top: `${task.y}%`,
            animation: `floatTask ${5 + task.delay}s ease-in-out infinite`,
            animationDelay: `${task.delay}s`,
          }}
        >
          <div className="flex items-center gap-2 px-3 py-2 bg-green-500/20 border border-green-500/30 rounded-lg backdrop-blur-sm">
            <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
            <span className="text-xs sm:text-sm text-green-300 whitespace-nowrap">
              {t.completedTasks[task.taskIndex]}
            </span>
          </div>
        </div>
      ))}

      {/* Content - centered */}
      <div className="relative z-10 text-center max-w-md mx-auto">
        {/* Animated 404 with card styling */}
        <div className="relative mb-6">
          <div className="relative inline-block">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl blur-xl opacity-50" />
            <div className="relative bg-dark-800/80 border-2 border-purple-500/50 rounded-2xl p-6 backdrop-blur-sm">
              <h1 className="text-[80px] sm:text-[100px] font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 leading-none">
                404
              </h1>
            </div>
          </div>
        </div>

        {/* Task-themed icons */}
        <div className="flex justify-center gap-3 mb-4">
          <div className="p-2 bg-red-500/20 rounded-lg">
            <ListTodo className="w-5 h-5 text-red-400" />
          </div>
          <div className="p-2 bg-yellow-500/20 rounded-lg">
            <Swords className="w-5 h-5 text-yellow-400" />
          </div>
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Scroll className="w-5 h-5 text-purple-400" />
          </div>
        </div>

        <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">{t.title}</h2>
        <p className="text-gray-400 mb-2 text-sm sm:text-base">
          {t.description}
        </p>
        <p className="text-gray-500 text-xs sm:text-sm mb-8">
          {t.hint}
        </p>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-xl hover:opacity-90 transition-all hover:scale-105 active:scale-95"
          >
            <Home className="w-5 h-5" />
            {isLoggedIn ? t.toTasks : t.toHome}
          </Link>
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-700/50 text-white font-semibold rounded-xl hover:bg-gray-600/50 transition-all hover:scale-105 active:scale-95"
          >
            <ArrowLeft className="w-5 h-5" />
            {t.back}
          </button>
        </div>
      </div>

      {/* Decorative gradient orbs - also on sides */}
      <div className="absolute top-20 left-5 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl animate-float" />
      <div className="absolute bottom-32 right-5 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl animate-float-delayed" />

      <style jsx>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(var(--rotation, 0deg)); }
          50% { transform: translateY(-20px) rotate(var(--rotation, 0deg)); }
        }
        @keyframes floatTask {
          0%, 100% { transform: translateY(0px) translateX(0px); opacity: 0.8; }
          50% { transform: translateY(-12px) translateX(5px); opacity: 1; }
        }
        .animate-float {
          animation: float 6s ease-in-out infinite;
        }
        .animate-float-delayed {
          animation: float 8s ease-in-out infinite;
          animation-delay: 1s;
        }
      `}</style>
    </div>
  );
}
