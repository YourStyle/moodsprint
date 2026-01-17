import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../providers/auth_provider.dart';
import '../services/auth_service.dart';
import '../services/notification_service.dart';
import '../utils/constants.dart';

class MainWebViewScreen extends StatefulWidget {
  const MainWebViewScreen({super.key});

  @override
  State<MainWebViewScreen> createState() => _MainWebViewScreenState();
}

class _MainWebViewScreenState extends State<MainWebViewScreen> {
  late WebViewController _controller;
  bool _isLoading = true;
  bool _hasError = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initWebView();
    _registerFcmToken();
  }

  void _initWebView() {
    final authProvider = context.read<AuthProvider>();
    final token = authProvider.token;

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(AppColors.background)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (url) {
            if (mounted) {
              setState(() {
                _isLoading = true;
                _hasError = false;
              });
            }
          },
          onPageFinished: (url) {
            if (mounted) {
              setState(() {
                _isLoading = false;
              });
            }

            // Inject token into localStorage for the web app to use
            // Use 'auth_token' to match frontend's api.ts localStorage key
            if (token != null) {
              _controller.runJavaScript('''
                localStorage.setItem('auth_token', '$token');
                localStorage.setItem('moodsprint_mobile_app', 'true');
              ''');
            }
          },
          onWebResourceError: (error) {
            if (mounted) {
              setState(() {
                _isLoading = false;
                _hasError = true;
                _errorMessage = error.description;
              });
            }
          },
          onNavigationRequest: (request) {
            // Handle external links
            final uri = Uri.parse(request.url);
            if (!request.url.startsWith(ApiConfig.baseUrl)) {
              // Open external links in browser
              // You can use url_launcher here
              return NavigationDecision.prevent;
            }
            return NavigationDecision.navigate;
          },
        ),
      )
      ..addJavaScriptChannel(
        'FlutterBridge',
        onMessageReceived: (message) {
          _handleJsMessage(message.message);
        },
      );

    // Load the web app with mobile app indicator
    _controller.loadRequest(
      Uri.parse('${ApiConfig.baseUrl}?app=mobile'),
      headers: {
        'Authorization': 'Bearer $token',
        'X-Mobile-App': 'true',
      },
    );
  }

  Future<void> _registerFcmToken() async {
    final authProvider = context.read<AuthProvider>();
    final authToken = authProvider.token;
    final fcmToken = NotificationService().fcmToken;

    if (authToken != null && fcmToken != null) {
      await AuthService().registerFcmToken(authToken, fcmToken);
    }
  }

  void _handleJsMessage(String message) {
    // Handle messages from web app
    // For example: logout request
    if (message == 'logout') {
      _handleLogout();
    }
  }

  Future<void> _handleLogout() async {
    final authProvider = context.read<AuthProvider>();
    await authProvider.logout();

    if (mounted) {
      Navigator.of(context).pushReplacementNamed('/login');
    }
  }

  Future<void> _reload() async {
    setState(() {
      _isLoading = true;
      _hasError = false;
    });
    await _controller.reload();
  }

  Future<bool> _onWillPop() async {
    if (await _controller.canGoBack()) {
      await _controller.goBack();
      return false;
    }
    return true;
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: _onWillPop,
      child: Scaffold(
        body: Container(
          decoration: const BoxDecoration(
            gradient: AppColors.backgroundGradient,
          ),
          child: SafeArea(
            child: Stack(
              children: [
                // WebView
                if (!_hasError)
                  WebViewWidget(controller: _controller),

                // Loading indicator
                if (_isLoading)
                  Container(
                    color: AppColors.background,
                    child: const Center(
                      child: CircularProgressIndicator(
                        valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
                      ),
                    ),
                  ),

                // Error state
                if (_hasError)
                  _buildErrorState(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return Container(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.error.withOpacity(0.1),
            ),
            child: const Icon(
              Icons.wifi_off,
              size: 40,
              color: AppColors.error,
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'Нет подключения',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _errorMessage ?? AppStrings.errorNetwork,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
            label: const Text('Повторить'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
            ),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: _handleLogout,
            child: const Text(
              AppStrings.logout,
              style: TextStyle(color: AppColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }
}
