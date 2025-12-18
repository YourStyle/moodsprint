/**
 * Telegram WebApp SDK utilities.
 */

import type { TelegramWebApp } from '@/domain/types';

export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window === 'undefined') return null;
  return window.Telegram?.WebApp || null;
}

export function isTelegramWebApp(): boolean {
  const webApp = getTelegramWebApp();
  return webApp !== null && !!webApp.initData;
}

export function getTelegramInitData(): string | null {
  const webApp = getTelegramWebApp();
  return webApp?.initData || null;
}

export function getTelegramUser() {
  const webApp = getTelegramWebApp();
  return webApp?.initDataUnsafe?.user || null;
}

export function getTelegramTheme() {
  const webApp = getTelegramWebApp();
  if (!webApp) return null;

  return {
    colorScheme: webApp.colorScheme,
    themeParams: webApp.themeParams,
    backgroundColor: webApp.backgroundColor,
    headerColor: webApp.headerColor,
  };
}

export function expandTelegramWebApp() {
  const webApp = getTelegramWebApp();
  if (webApp && !webApp.isExpanded) {
    webApp.expand();
  }
}

export function requestFullscreen() {
  const webApp = getTelegramWebApp();
  if (webApp && !webApp.isFullscreen && webApp.requestFullscreen) {
    webApp.requestFullscreen();
  }
}

export function exitFullscreen() {
  const webApp = getTelegramWebApp();
  if (webApp && webApp.isFullscreen && webApp.exitFullscreen) {
    webApp.exitFullscreen();
  }
}

export function enableClosingConfirmation() {
  const webApp = getTelegramWebApp();
  if (webApp && webApp.enableClosingConfirmation) {
    webApp.enableClosingConfirmation();
  }
}

export function disableClosingConfirmation() {
  const webApp = getTelegramWebApp();
  if (webApp && webApp.disableClosingConfirmation) {
    webApp.disableClosingConfirmation();
  }
}

export function disableVerticalSwipes() {
  const webApp = getTelegramWebApp();
  if (webApp && webApp.disableVerticalSwipes) {
    webApp.disableVerticalSwipes();
  }
}

export function enableVerticalSwipes() {
  const webApp = getTelegramWebApp();
  if (webApp && webApp.enableVerticalSwipes) {
    webApp.enableVerticalSwipes();
  }
}

export function isMobileDevice(): boolean {
  const webApp = getTelegramWebApp();
  if (!webApp) return false;

  const platform = webApp.platform?.toLowerCase() || '';
  // Mobile platforms: ios, android
  // Non-mobile: tdesktop, macos, web, weba, webk, unigram
  return platform === 'ios' || platform === 'android';
}

export function readyTelegramWebApp() {
  const webApp = getTelegramWebApp();
  webApp?.ready();
}

export function closeTelegramWebApp() {
  const webApp = getTelegramWebApp();
  webApp?.close();
}

export function hapticFeedback(type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error') {
  const webApp = getTelegramWebApp();
  if (!webApp) return;

  switch (type) {
    case 'light':
    case 'medium':
    case 'heavy':
      webApp.HapticFeedback.impactOccurred(type);
      break;
    case 'success':
    case 'warning':
    case 'error':
      webApp.HapticFeedback.notificationOccurred(type);
      break;
  }
}

export function showTelegramAlert(message: string, callback?: () => void) {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.showAlert(message, callback);
  } else {
    alert(message);
    callback?.();
  }
}

export function showTelegramConfirm(message: string, callback: (confirmed: boolean) => void) {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.showConfirm(message, callback);
  } else {
    const confirmed = confirm(message);
    callback(confirmed);
  }
}

export function setMainButton(config: {
  text: string;
  onClick: () => void;
  isVisible?: boolean;
  isActive?: boolean;
}) {
  const webApp = getTelegramWebApp();
  if (!webApp) return;

  webApp.MainButton.setText(config.text);
  webApp.MainButton.onClick(config.onClick);

  if (config.isVisible !== false) {
    webApp.MainButton.show();
  }

  if (config.isActive !== false) {
    webApp.MainButton.enable();
  }
}

export function hideMainButton() {
  const webApp = getTelegramWebApp();
  webApp?.MainButton.hide();
}

let backButtonCallback: (() => void) | null = null;

export function showBackButton(onClick: () => void) {
  const webApp = getTelegramWebApp();
  if (!webApp) return;

  // Remove previous callback if exists
  if (backButtonCallback) {
    webApp.BackButton.offClick(backButtonCallback);
  }

  backButtonCallback = onClick;
  webApp.BackButton.onClick(onClick);
  webApp.BackButton.show();
}

export function hideBackButton() {
  const webApp = getTelegramWebApp();
  if (!webApp) return;

  if (backButtonCallback) {
    webApp.BackButton.offClick(backButtonCallback);
    backButtonCallback = null;
  }
  webApp.BackButton.hide();
}

export function getStartParam(): string | null {
  const webApp = getTelegramWebApp();
  return webApp?.initDataUnsafe?.start_param || null;
}

export function openTelegramLink(url: string) {
  const webApp = getTelegramWebApp();
  if (webApp && webApp.openTelegramLink) {
    webApp.openTelegramLink(url);
  } else {
    window.open(url, '_blank');
  }
}

export function shareInviteLink(userId: number, text?: string) {
  const webApp = getTelegramWebApp();
  const botUsername = process.env.NEXT_PUBLIC_BOT_USERNAME || 'moodsprintbot';
  const inviteParam = `invite_${userId}`;
  const shareUrl = `https://t.me/${botUsername}/app?startapp=${inviteParam}`;
  const shareText = text || 'Join me in MoodSprint!';

  const telegramShareUrl = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`;

  if (webApp && webApp.openTelegramLink) {
    webApp.openTelegramLink(telegramShareUrl);
  } else {
    window.open(telegramShareUrl, '_blank');
  }
}
