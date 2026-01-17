import 'package:flutter/material.dart';

class AppColors {
  static const Color background = Color(0xFF0A0612);
  static const Color surface = Color(0xFF1A1433);
  static const Color surfaceLight = Color(0xFF2A2053);
  static const Color primary = Color(0xFF7C3AED);
  static const Color primaryLight = Color(0xFFA855F7);
  static const Color accent = Color(0xFF60A5FA);
  static const Color border = Color(0xFF3D3456);
  static const Color textPrimary = Color(0xFFFFFFFF);
  static const Color textSecondary = Color(0xFFA5A3B3);
  static const Color textMuted = Color(0xFF6B6880);
  static const Color error = Color(0xFFEF4444);
  static const Color success = Color(0xFF22C55E);
  static const Color warning = Color(0xFFF59E0B);

  // Gradients
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF7C3AED), Color(0xFFA855F7)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    colors: [Color(0xFF0A0612), Color(0xFF0F0A1E), Color(0xFF1A1433)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );
}

class ApiConfig {
  // Change this to your production URL
  static const String baseUrl = 'https://moodsprint.app';
  static const String apiUrl = '$baseUrl/api/v1';

  // For development
  // static const String baseUrl = 'http://localhost:8080';
  // static const String apiUrl = '$baseUrl/api/v1';
}

class AppStrings {
  static const String appName = 'MoodSprint';

  // Auth
  static const String login = 'Войти';
  static const String register = 'Регистрация';
  static const String email = 'Email';
  static const String password = 'Пароль';
  static const String confirmPassword = 'Подтвердите пароль';
  static const String firstName = 'Имя';
  static const String forgotPassword = 'Забыли пароль?';
  static const String noAccount = 'Нет аккаунта?';
  static const String hasAccount = 'Уже есть аккаунт?';
  static const String createAccount = 'Создать аккаунт';
  static const String logout = 'Выйти';

  // Biometrics
  static const String useBiometrics = 'Использовать биометрию';
  static const String biometricsReason = 'Войдите с помощью биометрии';

  // Errors
  static const String errorGeneric = 'Произошла ошибка. Попробуйте позже.';
  static const String errorNetwork = 'Проверьте подключение к интернету';
  static const String errorInvalidCredentials = 'Неверный email или пароль';
  static const String errorEmailExists = 'Этот email уже зарегистрирован';
  static const String errorPasswordMismatch = 'Пароли не совпадают';
  static const String errorInvalidEmail = 'Введите корректный email';
  static const String errorPasswordTooShort = 'Пароль должен быть не менее 6 символов';
}
