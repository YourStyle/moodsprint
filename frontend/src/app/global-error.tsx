'use client';

import { useEffect } from 'react';
import { AlertOctagon, Home, RotateCcw } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Global error:', error);
  }, [error]);

  return (
    <html lang="ru">
      <body className="bg-gray-900 text-white">
        <div className="min-h-screen flex flex-col items-center justify-center p-4">
          {/* Critical error icon */}
          <div className="mb-8 p-6 bg-red-500/20 rounded-full animate-pulse">
            <AlertOctagon className="w-16 h-16 text-red-500" />
          </div>

          {/* Message */}
          <h1 className="text-3xl font-bold mb-2">Критическая ошибка</h1>
          <p className="text-gray-400 mb-8 text-center max-w-md">
            Произошла серьёзная ошибка приложения. Пожалуйста, перезагрузите страницу.
          </p>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={reset}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-red-600 text-white font-semibold rounded-xl hover:bg-red-700 transition-colors"
            >
              <RotateCcw className="w-5 h-5" />
              Перезагрузить
            </button>
            <a
              href="/"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-700 text-white font-semibold rounded-xl hover:bg-gray-600 transition-colors"
            >
              <Home className="w-5 h-5" />
              На главную
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
