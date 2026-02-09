'use client';

import { useEffect, useState } from 'react';
import { Home, RotateCcw, AlertTriangle, Zap } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [glitchText, setGlitchText] = useState('500');
  const [shakeCount, setShakeCount] = useState(0);

  useEffect(() => {
    console.error('Application error:', error);
  }, [error]);

  // Glitch effect on the number
  useEffect(() => {
    const chars = '!@#$%^&*()_+{}|:<>?';
    const interval = setInterval(() => {
      const glitched = '500'
        .split('')
        .map((char) => (Math.random() > 0.7 ? chars[Math.floor(Math.random() * chars.length)] : char))
        .join('');
      setGlitchText(glitched);
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const handleShake = () => {
    setShakeCount((prev) => prev + 1);
    if (shakeCount >= 4) {
      reset();
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Animated warning stripes background */}
      <div className="absolute inset-0 opacity-5">
        <div
          className="w-full h-full"
          style={{
            backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, #f59e0b 10px, #f59e0b 20px)',
            animation: 'stripes 20s linear infinite',
          }}
        />
      </div>

      {/* Electric sparks decoration */}
      <div className="absolute top-1/4 left-1/4 text-yellow-400 animate-ping">
        <Zap className="w-8 h-8" />
      </div>
      <div className="absolute bottom-1/3 right-1/4 text-yellow-400 animate-ping" style={{ animationDelay: '0.5s' }}>
        <Zap className="w-6 h-6" />
      </div>
      <div className="absolute top-1/3 right-1/3 text-yellow-400 animate-ping" style={{ animationDelay: '1s' }}>
        <Zap className="w-4 h-4" />
      </div>

      {/* Content */}
      <div className="relative z-10 text-center">
        {/* Glitchy 500 */}
        <div
          className="relative mb-6 cursor-pointer select-none"
          onClick={handleShake}
        >
          <div
            className={`text-[120px] font-black text-red-500 leading-none ${shakeCount > 0 ? 'animate-shake' : ''}`}
            style={{
              textShadow: '2px 0 #00ffff, -2px 0 #ff00ff',
            }}
          >
            {glitchText}
          </div>
          <div className="absolute inset-0 text-[120px] font-black text-red-500/20 blur-lg leading-none">
            500
          </div>
        </div>

        {/* Warning icon */}
        <div className="flex justify-center mb-4">
          <div className="p-4 bg-red-500/20 rounded-full animate-pulse">
            <AlertTriangle className="w-12 h-12 text-red-400" />
          </div>
        </div>

        {/* Message */}
        <h2 className="text-2xl font-bold text-white mb-2">Что-то пошло не так</h2>
        <p className="text-gray-400 mb-2 max-w-md">
          Произошла непредвиденная ошибка. Наши разработчики уже в курсе.
        </p>
        <p className="text-gray-500 text-sm mb-8 max-w-md">
          {shakeCount < 5
            ? `Нажми на 500 ещё ${5 - shakeCount} раз${5 - shakeCount > 1 ? '' : ''} чтобы перезагрузить!`
            : 'Перезагрузка...'}
        </p>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={reset}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-red-600 to-orange-600 text-white font-semibold rounded-xl hover:opacity-90 transition-all hover:scale-105 active:scale-95"
          >
            <RotateCcw className="w-5 h-5" />
            Попробовать снова
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-700/50 text-white font-semibold rounded-xl hover:bg-gray-600/50 transition-all hover:scale-105 active:scale-95"
          >
            <Home className="w-5 h-5" />
            На главную
          </a>
        </div>

        {/* Error details (development) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-8 p-4 bg-gray-800/50 rounded-xl text-left max-w-lg mx-auto">
            <p className="text-xs text-gray-500 font-mono break-all">{error.message}</p>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes stripes {
          0% { background-position: 0 0; }
          100% { background-position: 100px 0; }
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
          20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
      `}</style>
    </div>
  );
}
