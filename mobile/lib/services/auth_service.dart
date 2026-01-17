import 'dart:convert';
import 'package:http/http.dart' as http;
import '../utils/constants.dart';

class AuthResult {
  final bool success;
  final String? token;
  final Map<String, dynamic>? user;
  final String? error;

  AuthResult({
    required this.success,
    this.token,
    this.user,
    this.error,
  });
}

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  Future<AuthResult> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiUrl}/auth/login'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'email': email,
          'password': password,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        return AuthResult(
          success: true,
          token: data['data']['access_token'],
          user: data['data']['user'],
        );
      } else {
        return AuthResult(
          success: false,
          error: data['error']?['message'] ?? AppStrings.errorInvalidCredentials,
        );
      }
    } catch (e) {
      print('Login error: $e');
      return AuthResult(
        success: false,
        error: AppStrings.errorNetwork,
      );
    }
  }

  Future<AuthResult> register(String email, String password, String firstName) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiUrl}/auth/register'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'email': email,
          'password': password,
          'first_name': firstName,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 201 && data['success'] == true) {
        return AuthResult(
          success: true,
          token: data['data']['access_token'],
          user: data['data']['user'],
        );
      } else {
        String errorMessage = AppStrings.errorGeneric;
        if (data['error']?['code'] == 'EMAIL_EXISTS') {
          errorMessage = AppStrings.errorEmailExists;
        } else if (data['error']?['message'] != null) {
          errorMessage = data['error']['message'];
        }
        return AuthResult(
          success: false,
          error: errorMessage,
        );
      }
    } catch (e) {
      print('Register error: $e');
      return AuthResult(
        success: false,
        error: AppStrings.errorNetwork,
      );
    }
  }

  Future<AuthResult> getCurrentUser(String token) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiUrl}/auth/me'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        return AuthResult(
          success: true,
          token: token,
          user: data['data']['user'],
        );
      } else {
        return AuthResult(
          success: false,
          error: 'Token invalid',
        );
      }
    } catch (e) {
      print('Get current user error: $e');
      return AuthResult(
        success: false,
        error: AppStrings.errorNetwork,
      );
    }
  }

  Future<void> registerFcmToken(String authToken, String fcmToken) async {
    try {
      await http.post(
        Uri.parse('${ApiConfig.apiUrl}/auth/fcm-token'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({
          'fcm_token': fcmToken,
        }),
      );
    } catch (e) {
      print('FCM token registration error: $e');
    }
  }
}
