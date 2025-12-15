export const translations = {
  ru: {
    // Common
    loading: 'Загрузка...',
    save: 'Сохранить',
    cancel: 'Отмена',
    delete: 'Удалить',
    edit: 'Редактировать',
    add: 'Добавить',
    close: 'Закрыть',
    back: 'Назад',
    next: 'Далее',
    done: 'Готово',
    error: 'Ошибка',
    success: 'Успех',

    // Navigation
    home: 'Главная',
    tasks: 'Задачи',
    profile: 'Профиль',
    settings: 'Настройки',
    arena: 'Арена',
    deck: 'Колода',

    // Greetings
    goodMorning: 'Доброе утро',
    goodAfternoon: 'Добрый день',
    goodEvening: 'Добрый вечер',
    friend: 'друг',

    // Days
    today: 'Сегодня',
    tomorrow: 'Завтра',
    yesterday: 'Вчера',

    // Week days
    sun: 'Вс',
    mon: 'Пн',
    tue: 'Вт',
    wed: 'Ср',
    thu: 'Чт',
    fri: 'Пт',
    sat: 'Сб',

    // Tasks
    createTask: 'Создать задачу',
    taskTitle: 'Название задачи',
    taskDescription: 'Описание (необязательно)',
    taskPlaceholder: 'Что нужно сделать?',
    descriptionPlaceholder: 'Добавьте подробности...',
    whenToComplete: 'Когда выполнить',
    other: 'Другой',
    noTasksForDate: 'Нет задач на',
    viewAll: 'Посмотреть все',

    // Priority
    priority: 'Приоритет',
    priorityLow: 'Низкий',
    priorityMedium: 'Средний',
    priorityHigh: 'Высокий',

    // Status
    statusPending: 'Ожидает',
    statusInProgress: 'В работе',
    statusCompleted: 'Готово',
    all: 'Все',

    // Mood
    howAreYouFeeling: 'Как ты себя чувствуешь?',
    mood: 'Настроение',
    energy: 'Энергия',

    // Focus
    focus: 'Фокус',
    startFocus: 'Начать',
    pause: 'Пауза',
    resume: 'Продолжить',
    complete: 'Завершить',

    // Profile
    level: 'Уровень',
    experience: 'Опыт',
    achievements: 'Достижения',
    streak: 'Серия',
    days: 'дней',

    // Settings
    language: 'Язык',
    notifications: 'Уведомления',
    theme: 'Тема',

    // Telegram
    openInTelegram: 'Открыть в Telegram',
    pleaseOpenViaTelegram: 'Пожалуйста, откройте приложение через Telegram для продолжения.',

    // App description
    appDescription: 'Это твой личный помощник, который знает, как распределить дела для максимальной эффективности.',

    // Cards
    attack: 'Атака',
    defense: 'Защита',
    health: 'Здоровье',

    // Battle
    battle: 'Сражение',
    victory: 'Победа',
    defeat: 'Поражение',
    yourTurn: 'Ваш ход',
    enemyTurn: 'Ход противника',
  },

  en: {
    // Common
    loading: 'Loading...',
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    close: 'Close',
    back: 'Back',
    next: 'Next',
    done: 'Done',
    error: 'Error',
    success: 'Success',

    // Navigation
    home: 'Home',
    tasks: 'Tasks',
    profile: 'Profile',
    settings: 'Settings',
    arena: 'Arena',
    deck: 'Deck',

    // Greetings
    goodMorning: 'Good morning',
    goodAfternoon: 'Good afternoon',
    goodEvening: 'Good evening',
    friend: 'friend',

    // Days
    today: 'Today',
    tomorrow: 'Tomorrow',
    yesterday: 'Yesterday',

    // Week days
    sun: 'Sun',
    mon: 'Mon',
    tue: 'Tue',
    wed: 'Wed',
    thu: 'Thu',
    fri: 'Fri',
    sat: 'Sat',

    // Tasks
    createTask: 'Create task',
    taskTitle: 'Task title',
    taskDescription: 'Description (optional)',
    taskPlaceholder: 'What needs to be done?',
    descriptionPlaceholder: 'Add details...',
    whenToComplete: 'When to complete',
    other: 'Other',
    noTasksForDate: 'No tasks for',
    viewAll: 'View all',

    // Priority
    priority: 'Priority',
    priorityLow: 'Low',
    priorityMedium: 'Medium',
    priorityHigh: 'High',

    // Status
    statusPending: 'Pending',
    statusInProgress: 'In progress',
    statusCompleted: 'Completed',
    all: 'All',

    // Mood
    howAreYouFeeling: 'How are you feeling?',
    mood: 'Mood',
    energy: 'Energy',

    // Focus
    focus: 'Focus',
    startFocus: 'Start',
    pause: 'Pause',
    resume: 'Resume',
    complete: 'Complete',

    // Profile
    level: 'Level',
    experience: 'Experience',
    achievements: 'Achievements',
    streak: 'Streak',
    days: 'days',

    // Settings
    language: 'Language',
    notifications: 'Notifications',
    theme: 'Theme',

    // Telegram
    openInTelegram: 'Open in Telegram',
    pleaseOpenViaTelegram: 'Please open the app via Telegram to continue.',

    // App description
    appDescription: 'Your personal assistant that knows how to organize tasks for maximum efficiency.',

    // Cards
    attack: 'Attack',
    defense: 'Defense',
    health: 'Health',

    // Battle
    battle: 'Battle',
    victory: 'Victory',
    defeat: 'Defeat',
    yourTurn: 'Your turn',
    enemyTurn: 'Enemy turn',
  },
} as const;

export type Language = keyof typeof translations;
export type TranslationKey = keyof typeof translations.ru;
