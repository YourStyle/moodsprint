import type { Metadata, Viewport } from 'next';
import { Nunito_Sans } from 'next/font/google';
import Script from 'next/script';
import './globals.css';
import { Providers } from './providers';
import { Navigation } from '@/components/Navigation';
import { ScrollBackdrop } from '@/components/ui';

const nunitoSans = Nunito_Sans({ subsets: ['latin', 'cyrillic'], weight: ['400', '500', '600', '700', '800'] });

export const metadata: Metadata = {
  title: 'MoodSprint',
  description: 'Адаптивное управление задачами на основе твоего настроения',
  manifest: '/manifest.json',
  icons: {
    icon: '/moodsprint.ico',
    shortcut: '/moodsprint.ico',
    apple: '/moodsprint.ico',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <head>
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body className={nunitoSans.className}>
        <Providers>
          <ScrollBackdrop />
          <div className="min-h-screen flex flex-col pt-safe">
            <main className="flex-1 pb-20">{children}</main>
            <Navigation />
          </div>
        </Providers>
      </body>
    </html>
  );
}
