import 'package:flutter/foundation.dart';
import '../services/api_service.dart';

class AuthProvider with ChangeNotifier {
  final ApiService _apiService;
  bool _isLoading = false;
  String? _errorMessage;
  bool _isGuestMode = false;

  AuthProvider(this._apiService);

  bool get isAuthenticated => _apiService.isAuthenticated || _isGuestMode;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isGuestMode => _isGuestMode;

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final success = await _apiService.login(username, password);
      _isLoading = false;

      if (!success) {
        _errorMessage = 'Invalid username or password';
      }

      notifyListeners();
      return success;
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'An error occurred: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<bool> register(String username, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final success = await _apiService.register(username, password);
      _isLoading = false;

      if (!success) {
        _errorMessage = 'Registration failed. Username may already exist.';
      }

      notifyListeners();
      return success;
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'An error occurred: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _apiService.logout();
    _isGuestMode = false;
    notifyListeners();
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }

  void continueAsGuest() {
    _isGuestMode = true;
    _errorMessage = null;
    notifyListeners();
  }
}
