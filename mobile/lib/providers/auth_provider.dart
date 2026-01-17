import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../services/auth_service.dart';
import '../services/biometric_service.dart';

class AuthProvider with ChangeNotifier {
  final AuthService _authService = AuthService();
  final BiometricService _biometricService = BiometricService();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  static const _tokenKey = 'auth_token';
  static const _emailKey = 'saved_email';
  static const _biometricEnabledKey = 'biometric_enabled';

  String? _token;
  Map<String, dynamic>? _user;
  bool _isLoading = false;
  String? _error;
  bool _biometricEnabled = false;

  // Getters
  String? get token => _token;
  Map<String, dynamic>? get user => _user;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _token != null && _user != null;
  bool get biometricEnabled => _biometricEnabled;

  // Clear error
  void clearError() {
    _error = null;
    notifyListeners();
  }

  // Try to auto login with saved token
  Future<bool> tryAutoLogin() async {
    _isLoading = true;
    notifyListeners();

    try {
      final savedToken = await _storage.read(key: _tokenKey);
      final biometricEnabled = await _storage.read(key: _biometricEnabledKey);
      _biometricEnabled = biometricEnabled == 'true';

      if (savedToken != null) {
        // Verify token is still valid
        final result = await _authService.getCurrentUser(savedToken);
        if (result.success) {
          _token = savedToken;
          _user = result.user;
          _isLoading = false;
          notifyListeners();
          return true;
        } else {
          // Token invalid, clear it
          await _storage.delete(key: _tokenKey);
        }
      }
    } catch (e) {
      print('Auto login error: $e');
    }

    _isLoading = false;
    notifyListeners();
    return false;
  }

  // Login with email and password
  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    final result = await _authService.login(email, password);

    if (result.success) {
      _token = result.token;
      _user = result.user;

      // Save token securely
      await _storage.write(key: _tokenKey, value: _token);
      await _storage.write(key: _emailKey, value: email);

      _isLoading = false;
      notifyListeners();
      return true;
    } else {
      _error = result.error;
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // Register new user
  Future<bool> register(String email, String password, String firstName) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    final result = await _authService.register(email, password, firstName);

    if (result.success) {
      _token = result.token;
      _user = result.user;

      // Save token securely
      await _storage.write(key: _tokenKey, value: _token);
      await _storage.write(key: _emailKey, value: email);

      _isLoading = false;
      notifyListeners();
      return true;
    } else {
      _error = result.error;
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  // Login with biometrics
  Future<bool> loginWithBiometrics() async {
    if (!_biometricEnabled) return false;

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final authenticated = await _biometricService.authenticate();

      if (authenticated) {
        // Try to restore session with saved token
        final savedToken = await _storage.read(key: _tokenKey);
        if (savedToken != null) {
          final result = await _authService.getCurrentUser(savedToken);
          if (result.success) {
            _token = savedToken;
            _user = result.user;
            _isLoading = false;
            notifyListeners();
            return true;
          }
        }
      }
    } catch (e) {
      print('Biometric login error: $e');
    }

    _isLoading = false;
    notifyListeners();
    return false;
  }

  // Enable/disable biometric login
  Future<void> setBiometricEnabled(bool enabled) async {
    if (enabled) {
      final canUseBiometrics = await _biometricService.canUseBiometrics();
      if (!canUseBiometrics) return;
    }

    _biometricEnabled = enabled;
    await _storage.write(key: _biometricEnabledKey, value: enabled.toString());
    notifyListeners();
  }

  // Check if biometrics available
  Future<bool> canUseBiometrics() async {
    return await _biometricService.canUseBiometrics();
  }

  // Get saved email (for showing in login form)
  Future<String?> getSavedEmail() async {
    return await _storage.read(key: _emailKey);
  }

  // Logout
  Future<void> logout() async {
    _token = null;
    _user = null;
    _error = null;

    await _storage.delete(key: _tokenKey);
    // Keep email and biometric preference for convenience

    notifyListeners();
  }
}
