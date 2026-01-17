'use client';

import { useState, useEffect, useRef } from 'react';
import { Sparkles, CheckCircle, Brain, Trophy, Users, ArrowRight, Mail, Lock, User, Globe, Swords, Target, Layers, Star, Zap, Shield, RotateCcw } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import { authService } from '@/services';
import { useAppStore } from '@/lib/store';

type AuthMode = 'landing' | 'login' | 'register';
type Language = 'en' | 'ru';

const translations = {
  en: {
    // Header
    signIn: 'Sign In',
    language: 'EN',

    // Hero
    heroTitle: 'MoodSprint',
    heroSubtitle: 'Your mood. Your pace. Your productivity.',
    heroDescription1: 'Tired of rigid to-do lists that ignore how you feel?',
    heroDescription2: 'MoodSprint adapts tasks to your energy level. When you\'re exhausted, get smaller steps. When you\'re energized, tackle bigger challenges.',
    heroDescription3: 'Plus, earn cards, battle monsters, and make productivity actually fun.',
    getStarted: 'Get Started',

    // Features
    whyTitle: 'Why MoodSprint?',
    moodAwareTitle: 'Mood-Aware AI',
    moodAwareDesc: 'Tasks are broken down based on your current mood and energy level. Feeling tired? Get smaller, easier steps.',
    focusTitle: 'Focus Sessions',
    focusDesc: 'Built-in Pomodoro timer helps you stay focused. Track your productivity patterns over time.',
    gamificationTitle: 'Gamification',
    gamificationDesc: 'Earn XP, level up, and unlock achievements. Every completed task brings you closer to the next level.',
    socialTitle: 'Social Features',
    socialDesc: 'Add friends, trade cards, and compete on leaderboards. Stay motivated together.',

    // Cards section
    cardsTitle: 'Collect Unique Cards',
    cardsSubtitle: 'Build your ultimate deck',
    cardsDesc: 'Complete tasks to earn character cards from 5 different genres: Magic, Fantasy, Sci-Fi, Cyberpunk, and Anime. Each card has unique stats and abilities.',
    rarityCommon: 'Common',
    rarityUncommon: 'Uncommon',
    rarityRare: 'Rare',
    rarityEpic: 'Epic',
    rarityLegendary: 'Legendary',
    rarityDesc: 'Cards come in 5 rarities - from Common to Legendary. Legendary cards are unique and can only be owned by one player!',

    // Battle section
    battleTitle: 'Battle Monsters',
    battleSubtitle: 'Test your deck in combat',
    battleDesc: 'Enter the Arena and battle against AI-controlled monsters. Use strategy to deploy your cards, unleash special abilities, and defeat your enemies.',
    battleFeature1: 'Turn-based tactical combat',
    battleFeature2: 'Special card abilities',
    battleFeature3: 'Earn rewards for victories',

    // Campaign section
    campaignTitle: 'Epic Campaigns',
    campaignSubtitle: 'Embark on adventures',
    campaignDesc: 'Progress through story-driven campaigns with multiple chapters. Face increasingly difficult challenges and unlock exclusive rewards.',
    campaignFeature1: 'Story-driven narrative',
    campaignFeature2: 'Boss battles',
    campaignFeature3: 'Exclusive campaign rewards',

    // Trading section
    tradingTitle: 'Trade & Collect',
    tradingSubtitle: 'Complete your collection',
    tradingDesc: 'Trade cards with friends or sell them on the marketplace. Build the ultimate collection and create the perfect battle deck.',

    // CTA
    ctaTitle: 'Ready to make productivity fun?',
    ctaDesc: 'Join the adventure. Turn your tasks into victories.',
    startFree: 'Start Now',

    // Telegram
    telegramHint: 'Also available as a',
    telegramLink: 'Telegram Mini App',

    // Cards section extra
    dragHint: 'Drag to rotate',

    // Auth forms
    welcomeBack: 'Welcome Back',
    signInContinue: 'Sign in to continue to MoodSprint',
    email: 'Email',
    password: 'Password',
    signingIn: 'Signing in...',
    noAccount: "Don't have an account?",
    signUp: 'Sign up',
    backToLanding: 'Back to landing',
    createAccount: 'Create Account',
    joinMoodSprint: 'Join MoodSprint and boost your productivity',
    firstName: 'First Name',
    passwordHint: 'Password (min 6 characters)',
    creatingAccount: 'Creating account...',
    haveAccount: 'Already have an account?',

    // Footer
    copyright: '© 2026 MoodSprint. All rights reserved.',
  },
  ru: {
    // Header
    signIn: 'Войти',
    language: 'RU',

    // Hero
    heroTitle: 'MoodSprint',
    heroSubtitle: 'Твоё настроение. Твой темп. Твоя продуктивность.',
    heroDescription1: 'Устал от жёстких списков дел, которые игнорируют твоё состояние?',
    heroDescription2: 'MoodSprint адаптирует задачи под твою энергию. Устал — получи мелкие шаги. Полон сил — бери сложные задачи.',
    heroDescription3: 'А ещё — собирай карты, сражайся с монстрами и превращай продуктивность в игру.',
    getStarted: 'Начать',

    // Features
    whyTitle: 'Почему MoodSprint?',
    moodAwareTitle: 'ИИ учитывает настроение',
    moodAwareDesc: 'Задачи разбиваются с учётом вашего текущего настроения и энергии. Устали? Получите более мелкие и простые шаги.',
    focusTitle: 'Фокус-сессии',
    focusDesc: 'Встроенный Pomodoro-таймер помогает сохранять концентрацию. Отслеживайте свою продуктивность.',
    gamificationTitle: 'Геймификация',
    gamificationDesc: 'Зарабатывайте XP, повышайте уровень и открывайте достижения. Каждая выполненная задача приближает вас к следующему уровню.',
    socialTitle: 'Социальные функции',
    socialDesc: 'Добавляйте друзей, обменивайтесь картами и соревнуйтесь в рейтингах. Мотивируйте друг друга.',

    // Cards section
    cardsTitle: 'Собирайте уникальные карты',
    cardsSubtitle: 'Создайте свою идеальную колоду',
    cardsDesc: 'Выполняйте задачи, чтобы получать карты персонажей из 5 разных жанров: Магия, Фэнтези, Sci-Fi, Киберпанк и Аниме. Каждая карта имеет уникальные характеристики и способности.',
    rarityCommon: 'Обычная',
    rarityUncommon: 'Необычная',
    rarityRare: 'Редкая',
    rarityEpic: 'Эпическая',
    rarityLegendary: 'Легендарная',
    rarityDesc: 'Карты бывают 5 редкостей - от Обычных до Легендарных. Легендарные карты уникальны и могут принадлежать только одному игроку!',

    // Battle section
    battleTitle: 'Сражайтесь с монстрами',
    battleSubtitle: 'Испытайте свою колоду в бою',
    battleDesc: 'Входите на Арену и сражайтесь с монстрами под управлением ИИ. Используйте стратегию, применяйте способности карт и побеждайте врагов.',
    battleFeature1: 'Пошаговый тактический бой',
    battleFeature2: 'Особые способности карт',
    battleFeature3: 'Награды за победы',

    // Campaign section
    campaignTitle: 'Эпические кампании',
    campaignSubtitle: 'Отправляйтесь в приключения',
    campaignDesc: 'Проходите сюжетные кампании с множеством глав. Встречайте всё более сложные испытания и открывайте эксклюзивные награды.',
    campaignFeature1: 'Сюжетное повествование',
    campaignFeature2: 'Битвы с боссами',
    campaignFeature3: 'Эксклюзивные награды кампании',

    // Trading section
    tradingTitle: 'Обмен и коллекционирование',
    tradingSubtitle: 'Пополните свою коллекцию',
    tradingDesc: 'Обменивайтесь картами с друзьями или продавайте их на маркетплейсе. Соберите лучшую коллекцию и создайте идеальную боевую колоду.',

    // CTA
    ctaTitle: 'Готов сделать продуктивность интересной?',
    ctaDesc: 'Присоединяйся к приключению. Превращай задачи в победы.',
    startFree: 'Начать',

    // Telegram
    telegramHint: 'Также доступно как',
    telegramLink: 'Telegram Mini App',

    // Cards section extra
    dragHint: 'Потяни для вращения',

    // Auth forms
    welcomeBack: 'С возвращением',
    signInContinue: 'Войдите, чтобы продолжить',
    email: 'Email',
    password: 'Пароль',
    signingIn: 'Входим...',
    noAccount: 'Нет аккаунта?',
    signUp: 'Зарегистрироваться',
    backToLanding: 'На главную',
    createAccount: 'Создать аккаунт',
    joinMoodSprint: 'Присоединяйтесь и повышайте продуктивность',
    firstName: 'Имя',
    passwordHint: 'Пароль (мин. 6 символов)',
    creatingAccount: 'Создаём аккаунт...',
    haveAccount: 'Уже есть аккаунт?',

    // Footer
    copyright: '© 2026 MoodSprint. Все права защищены.',
  },
};

export function LandingPage() {
  const { setUser } = useAppStore();
  const [mode, setMode] = useState<AuthMode>('landing');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>('en');
  const [isScrolled, setIsScrolled] = useState(false);

  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');

  const t = translations[language];

  // Track scroll for header background
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'en' ? 'ru' : 'en');
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const result = await authService.login(email, password);
      if (result.success && result.data) {
        setUser(result.data.user);
      } else {
        setError(result.error?.message || 'Login failed');
      }
    } catch {
      setError('An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const result = await authService.register(email, password, firstName);
      if (result.success && result.data) {
        setUser(result.data.user);
      } else {
        setError(result.error?.message || 'Registration failed');
      }
    } catch {
      setError('An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Header component (sticky)
  const Header = () => (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-dark-900/95 backdrop-blur-xl border-b border-gray-800'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white">MoodSprint</span>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={toggleLanguage}
            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-colors text-gray-300 hover:text-white"
          >
            <Globe className="w-4 h-4" />
            <span className="text-sm font-medium">{t.language}</span>
          </button>
          <Button
            variant="gradient"
            size="sm"
            onClick={() => setMode('login')}
          >
            {t.signIn}
          </Button>
        </div>
      </div>
    </header>
  );

  if (mode === 'login') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-gradient-to-b from-dark-900 via-dark-800 to-dark-900">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">{t.welcomeBack}</h1>
            <p className="text-gray-400">{t.signInContinue}</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <Input
              type="email"
              placeholder={t.email}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              icon={<Mail className="w-5 h-5" />}
              required
            />
            <Input
              type="password"
              placeholder={t.password}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              icon={<Lock className="w-5 h-5" />}
              required
            />

            {error && (
              <div className="p-3 rounded-lg bg-red-500/20 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="gradient"
              size="lg"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? t.signingIn : t.signIn}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setMode('register');
                setError(null);
              }}
              className="text-purple-400 hover:text-purple-300 text-sm"
            >
              {t.noAccount} <span className="font-medium">{t.signUp}</span>
            </button>
          </div>

          <button
            onClick={() => setMode('landing')}
            className="mt-4 w-full text-center text-gray-500 hover:text-gray-400 text-sm"
          >
            {t.backToLanding}
          </button>
        </div>
      </div>
    );
  }

  if (mode === 'register') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-gradient-to-b from-dark-900 via-dark-800 to-dark-900">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">{t.createAccount}</h1>
            <p className="text-gray-400">{t.joinMoodSprint}</p>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <Input
              type="text"
              placeholder={t.firstName}
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              icon={<User className="w-5 h-5" />}
              required
            />
            <Input
              type="email"
              placeholder={t.email}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              icon={<Mail className="w-5 h-5" />}
              required
            />
            <Input
              type="password"
              placeholder={t.passwordHint}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              icon={<Lock className="w-5 h-5" />}
              minLength={6}
              required
            />

            {error && (
              <div className="p-3 rounded-lg bg-red-500/20 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="gradient"
              size="lg"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? t.creatingAccount : t.createAccount}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setMode('login');
                setError(null);
              }}
              className="text-purple-400 hover:text-purple-300 text-sm"
            >
              {t.haveAccount} <span className="font-medium">{t.signIn}</span>
            </button>
          </div>

          <button
            onClick={() => setMode('landing')}
            className="mt-4 w-full text-center text-gray-500 hover:text-gray-400 text-sm"
          >
            {t.backToLanding}
          </button>
        </div>
      </div>
    );
  }

  // Landing page
  return (
    <div className="min-h-screen bg-gradient-to-b from-dark-900 via-dark-800 to-dark-900">
      <Header />

      {/* Hero Section */}
      <div className="relative overflow-hidden pt-24">
        {/* Background effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-4xl mx-auto px-6 pt-16 pb-24 text-center">
          {/* Logo */}
          <div className="w-24 h-24 mx-auto mb-6 rounded-3xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
            <Sparkles className="w-12 h-12 text-white" />
          </div>

          <h1 className="text-5xl md:text-6xl font-bold text-white mb-4">
            {t.heroTitle}
          </h1>
          <p className="text-xl md:text-2xl text-purple-300 mb-6">
            {t.heroSubtitle}
          </p>
          <div className="text-gray-300 mb-8 max-w-2xl mx-auto text-lg space-y-3">
            <p className="text-gray-400">{t.heroDescription1}</p>
            <p>{t.heroDescription2}</p>
            <p className="text-purple-300">{t.heroDescription3}</p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              variant="gradient"
              size="lg"
              onClick={() => setMode('register')}
              className="px-8 text-lg"
            >
              {t.getStarted}
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => setMode('login')}
              className="px-8 text-lg"
            >
              {t.signIn}
            </Button>
          </div>

          {/* Telegram hint */}
          <p className="mt-8 text-sm text-gray-500">
            {t.telegramHint}{' '}
            <a
              href="https://t.me/moodsprint_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="text-purple-400 hover:text-purple-300"
            >
              {t.telegramLink}
            </a>
          </p>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-white text-center mb-12">
          {t.whyTitle}
        </h2>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <FeatureCard
            icon={<Brain className="w-6 h-6" />}
            title={t.moodAwareTitle}
            description={t.moodAwareDesc}
          />
          <FeatureCard
            icon={<CheckCircle className="w-6 h-6" />}
            title={t.focusTitle}
            description={t.focusDesc}
          />
          <FeatureCard
            icon={<Trophy className="w-6 h-6" />}
            title={t.gamificationTitle}
            description={t.gamificationDesc}
          />
          <FeatureCard
            icon={<Users className="w-6 h-6" />}
            title={t.socialTitle}
            description={t.socialDesc}
          />
        </div>
      </div>

      {/* Cards Collection Section */}
      <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-purple-500/30 flex items-center justify-center">
                  <Layers className="w-6 h-6 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white">{t.cardsTitle}</h3>
                  <p className="text-purple-300">{t.cardsSubtitle}</p>
                </div>
              </div>
              <p className="text-gray-300 mb-6">{t.cardsDesc}</p>

              {/* Rarity showcase */}
              <div className="flex flex-wrap gap-2 mb-4">
                <span className="px-3 py-1 rounded-full bg-gray-500/30 text-gray-300 text-sm">{t.rarityCommon}</span>
                <span className="px-3 py-1 rounded-full bg-green-500/30 text-green-300 text-sm">{t.rarityUncommon}</span>
                <span className="px-3 py-1 rounded-full bg-blue-500/30 text-blue-300 text-sm">{t.rarityRare}</span>
                <span className="px-3 py-1 rounded-full bg-purple-500/30 text-purple-300 text-sm">{t.rarityEpic}</span>
                <span className="px-3 py-1 rounded-full bg-amber-500/30 text-amber-300 text-sm">{t.rarityLegendary}</span>
              </div>
              <p className="text-gray-400 text-sm">{t.rarityDesc}</p>
            </div>

            <div className="flex justify-center">
              <InteractiveCardStack dragHint={t.dragHint} />
            </div>
          </div>
        </div>
      </div>

      {/* Battle Section */}
      <div className="py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="order-2 md:order-1 flex justify-center">
              <div className="relative w-64 h-64">
                {/* Battle visualization */}
                <div className="absolute inset-0 rounded-full bg-red-500/20 animate-pulse" />
                <div className="absolute inset-4 rounded-full bg-gradient-to-br from-red-600/40 to-orange-600/40 border-2 border-red-400/50 flex items-center justify-center">
                  <Swords className="w-20 h-20 text-red-300" />
                </div>
                <div className="absolute -top-2 -right-2 w-16 h-16 rounded-xl bg-purple-500/40 border border-purple-400/50 flex items-center justify-center">
                  <Zap className="w-8 h-8 text-purple-300" />
                </div>
                <div className="absolute -bottom-2 -left-2 w-16 h-16 rounded-xl bg-blue-500/40 border border-blue-400/50 flex items-center justify-center">
                  <Shield className="w-8 h-8 text-blue-300" />
                </div>
              </div>
            </div>

            <div className="order-1 md:order-2">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-red-500/30 flex items-center justify-center">
                  <Swords className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white">{t.battleTitle}</h3>
                  <p className="text-red-300">{t.battleSubtitle}</p>
                </div>
              </div>
              <p className="text-gray-300 mb-6">{t.battleDesc}</p>

              <ul className="space-y-3">
                <li className="flex items-center gap-3 text-gray-300">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  {t.battleFeature1}
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  {t.battleFeature2}
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  {t.battleFeature3}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Campaign Section */}
      <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-blue-500/30 flex items-center justify-center">
                  <Target className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white">{t.campaignTitle}</h3>
                  <p className="text-blue-300">{t.campaignSubtitle}</p>
                </div>
              </div>
              <p className="text-gray-300 mb-6">{t.campaignDesc}</p>

              <ul className="space-y-3">
                <li className="flex items-center gap-3 text-gray-300">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  {t.campaignFeature1}
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  {t.campaignFeature2}
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  {t.campaignFeature3}
                </li>
              </ul>
            </div>

            <div className="flex justify-center">
              {/* Campaign progress visualization */}
              <div className="relative">
                <div className="flex items-center gap-4">
                  {[1, 2, 3, 4, 5].map((chapter, i) => (
                    <div
                      key={chapter}
                      className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold ${
                        i < 3
                          ? 'bg-green-500/40 border border-green-400/50 text-green-300'
                          : i === 3
                          ? 'bg-blue-500/40 border border-blue-400/50 text-blue-300 animate-pulse'
                          : 'bg-gray-700/40 border border-gray-600/50 text-gray-500'
                      }`}
                    >
                      {chapter}
                    </div>
                  ))}
                </div>
                <div className="mt-4 h-2 rounded-full bg-gray-700/50 overflow-hidden">
                  <div className="h-full w-3/5 bg-gradient-to-r from-green-500 to-blue-500 rounded-full" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Section */}
      <div className="py-20">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-xl bg-green-500/30 flex items-center justify-center">
            <Users className="w-8 h-8 text-green-400" />
          </div>
          <h3 className="text-2xl font-bold text-white mb-2">{t.tradingTitle}</h3>
          <p className="text-green-300 mb-4">{t.tradingSubtitle}</p>
          <p className="text-gray-400 max-w-2xl mx-auto">{t.tradingDesc}</p>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="max-w-4xl mx-auto px-6 pb-8 text-center">
        <div className="bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-3xl p-10 border border-purple-500/30">
          <h3 className="text-2xl font-bold text-white mb-3">
            {t.ctaTitle}
          </h3>
          <p className="text-gray-400 mb-8">
            {t.ctaDesc}
          </p>
          <Button
            variant="gradient"
            size="lg"
            onClick={() => setMode('register')}
            className="px-10"
          >
            {t.startFree}
          </Button>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-800 py-8 text-center text-gray-500 text-sm">
        <p>{t.copyright}</p>
      </div>
    </div>
  );
}

function InteractiveCardStack({ dragHint }: { dragHint: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setStartPos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const deltaX = e.clientX - startPos.x;
    const deltaY = e.clientY - startPos.y;
    setRotation({
      x: Math.max(-30, Math.min(30, rotation.x - deltaY * 0.5)),
      y: Math.max(-45, Math.min(45, rotation.y + deltaX * 0.5)),
    });
    setStartPos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    setIsDragging(true);
    setStartPos({ x: touch.clientX, y: touch.clientY });
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;
    const touch = e.touches[0];
    const deltaX = touch.clientX - startPos.x;
    const deltaY = touch.clientY - startPos.y;
    setRotation({
      x: Math.max(-30, Math.min(30, rotation.x - deltaY * 0.5)),
      y: Math.max(-45, Math.min(45, rotation.y + deltaX * 0.5)),
    });
    setStartPos({ x: touch.clientX, y: touch.clientY });
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  const resetRotation = () => {
    setRotation({ x: 0, y: 0 });
  };

  const cards = [
    { gradient: 'from-amber-500 to-yellow-600', border: 'border-amber-400', icon: '👑', label: 'Legendary', z: 1 },
    { gradient: 'from-purple-500 to-pink-600', border: 'border-purple-400', icon: '🔮', label: 'Epic', z: 2 },
    { gradient: 'from-blue-500 to-cyan-600', border: 'border-blue-400', icon: '⚔️', label: 'Rare', z: 3 },
  ];

  return (
    <div className="relative">
      <div
        ref={containerRef}
        className="relative cursor-grab active:cursor-grabbing select-none"
        style={{ perspective: '1000px' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div
          className="relative w-56 h-72 transition-transform duration-100"
          style={{
            transformStyle: 'preserve-3d',
            transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
          }}
        >
          {cards.map((card, index) => (
            <div
              key={index}
              className={`absolute inset-0 w-48 h-64 rounded-2xl bg-gradient-to-br ${card.gradient} border-2 ${card.border}/50 shadow-xl flex flex-col items-center justify-center transition-all duration-300`}
              style={{
                transform: `translateZ(${(index - 1) * -20}px) rotateY(${(index - 1) * 8}deg) translateX(${(index - 1) * 15}px)`,
                zIndex: card.z,
              }}
            >
              <span className="text-5xl mb-2">{card.icon}</span>
              <span className="text-white/80 font-medium text-sm">{card.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Hint and reset */}
      <div className="flex items-center justify-center gap-4 mt-6">
        <span className="text-gray-500 text-sm flex items-center gap-2">
          <RotateCcw className="w-4 h-4" />
          {dragHint}
        </span>
        {(rotation.x !== 0 || rotation.y !== 0) && (
          <button
            onClick={resetRotation}
            className="text-purple-400 hover:text-purple-300 text-sm underline"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-dark-700/50 rounded-xl p-6 border border-gray-800 hover:border-purple-500/30 transition-colors">
      <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center text-purple-400 mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm">{description}</p>
    </div>
  );
}
