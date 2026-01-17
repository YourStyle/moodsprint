# MoodSprint Mobile App Setup Guide

## 1. Установка Flutter

### macOS (Homebrew)
```bash
brew install --cask flutter
```

### Проверка установки
```bash
flutter doctor
```

Должны быть ✓ для Flutter и iOS/Android (в зависимости от того, что хотите использовать).

---

## 2. Создание проекта

```bash
cd /Users/achukseev/WebstormProjects/moodsprint/mobile

# Создать iOS и Android папки
flutter create . --project-name moodsprint --org com.moodsprint

# Установить зависимости
flutter pub get
```

---

## 3. Firebase Setup (Push-уведомления)

### 3.1 Создание проекта Firebase

1. Перейди на https://console.firebase.google.com/
2. Нажми **"Create a project"** (или "Добавить проект")
3. Название: `moodsprint` или любое другое
4. Google Analytics: можно отключить (не обязательно для push)
5. Подожди создания проекта

### 3.2 Добавление Android приложения

1. В Firebase Console нажми на иконку Android
2. Заполни:
   - **Package name**: `com.moodsprint.moodsprint`
   - **App nickname**: `MoodSprint Android`
   - **SHA-1**: (опционально, нужен для некоторых сервисов)
3. Нажми **Register app**
4. Скачай `google-services.json`
5. Положи файл в:
   ```
   mobile/android/app/google-services.json
   ```

### 3.3 Добавление iOS приложения

1. В Firebase Console нажми на иконку iOS
2. Заполни:
   - **Bundle ID**: `com.moodsprint.moodsprint`
   - **App nickname**: `MoodSprint iOS`
3. Нажми **Register app**
4. Скачай `GoogleService-Info.plist`
5. Положи файл в:
   ```
   mobile/ios/Runner/GoogleService-Info.plist
   ```

### 3.4 Конфигурация Android

Отредактируй `android/build.gradle`:
```gradle
buildscript {
    dependencies {
        // Добавь эту строку
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

Отредактируй `android/app/build.gradle`:
```gradle
// В конце файла добавь
apply plugin: 'com.google.gms.google-services'
```

### 3.5 Конфигурация iOS

В Xcode (открой `ios/Runner.xcworkspace`):
1. Перейди в **Runner > Signing & Capabilities**
2. Нажми **+ Capability**
3. Добавь **Push Notifications**
4. Добавь **Background Modes** → включи **Remote notifications**

---

## 4. Настройка iOS (Face ID)

После `flutter create`, отредактируй `ios/Runner/Info.plist`:

Добавь внутрь `<dict>`:
```xml
<key>NSFaceIDUsageDescription</key>
<string>Используйте Face ID для быстрого входа в приложение</string>
```

---

## 5. Настройка Android (Biometric)

После `flutter create`, проверь что в `android/app/src/main/AndroidManifest.xml` есть:

```xml
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
<uses-permission android:name="android.permission.USE_FINGERPRINT"/>
```

Также для Android 13+ добавь:
```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
```

---

## 6. Запуск приложения

### iOS Simulator
```bash
# Открыть симулятор
open -a Simulator

# Запустить приложение
flutter run -d ios
```

### Android Emulator
```bash
# Запустить приложение (эмулятор должен быть открыт)
flutter run -d android
```

### Физическое устройство
```bash
# Подключи устройство по USB
flutter devices  # Посмотреть доступные устройства
flutter run -d <device_id>
```

---

## 7. Конфигурация API

В файле `lib/utils/constants.dart` измени `baseUrl`:

```dart
class ApiConfig {
  // Для локальной разработки
  static const String baseUrl = 'http://localhost:3000';

  // Для продакшена
  // static const String baseUrl = 'https://your-domain.com';
}
```

**Важно**: Для iOS симулятора `localhost` работает, но для Android эмулятора используй `10.0.2.2` вместо `localhost`.

---

## 8. Сборка для публикации

### iOS (App Store)
```bash
flutter build ios --release
```
Затем открой Xcode и архивируй через Product → Archive.

### Android (Google Play)
```bash
flutter build appbundle --release
```
Файл будет в `build/app/outputs/bundle/release/app-release.aab`

---

## Troubleshooting

### "CocoaPods not installed"
```bash
sudo gem install cocoapods
cd ios && pod install
```

### Android SDK not found
```bash
flutter config --android-sdk /path/to/android/sdk
```

### iOS signing issues
Открой `ios/Runner.xcworkspace` в Xcode и настрой Team в Signing & Capabilities.
