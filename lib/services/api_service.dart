import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/station.dart';

class ApiService {
  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  // API configuration
  late String baseUrl;
  String? _authToken;

  ApiService._internal() {
    // For Android emulators, localhost should be 10.0.2.2
    // This is a special IP that Android emulators use to communicate with the host machine
    if (Platform.isAndroid) {
      baseUrl = 'http://10.0.2.2:5000/api';
    } else {
      baseUrl = 'http://localhost:5000/api';
    }
  }

  // Initialize and load token from storage
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _authToken = prefs.getString('auth_token');
  }

  // Authentication methods
  Future<bool> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _authToken = data['access_token'];

        // Save token to storage
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('auth_token', _authToken!);

        return true;
      }
      return false;
    } catch (e) {
      print('Login error: $e');
      return false;
    }
  }

  Future<bool> register(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );

      return response.statusCode == 201;
    } catch (e) {
      print('Registration error: $e');
      return false;
    }
  }

  Future<void> logout() async {
    _authToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
  }

  bool get isAuthenticated => _authToken != null;

  // Station status methods
  Future<List<Station>> getStationStatuses() async {
    if (_authToken == null) {
      // If not authenticated, use guest mode
      return getStationStatusesAsGuest();
    }

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/stations'),
        headers: {
          'Authorization': 'Bearer $_authToken',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        return _parseStationResponse(response);
      } else if (response.statusCode == 401) {
        // Token expired or invalid
        await logout();
        throw Exception('Authentication expired');
      } else {
        throw Exception('Failed to load stations');
      }
    } catch (e) {
      print('Error getting station statuses: $e');
      return _getMockStations();
    }
  }

  // Get station statuses without authentication (guest mode)
  Future<List<Station>> getStationStatusesAsGuest() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/guest/stations'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return _parseStationResponse(response);
      } else {
        throw Exception('Failed to load stations as guest');
      }
    } catch (e) {
      print('Error getting station statuses as guest: $e');
      return _getMockStations();
    }
  }

  // Helper method to parse station response
  List<Station> _parseStationResponse(http.Response response) {
    final List<dynamic> data = jsonDecode(response.body);
    return data.map((station) {
      return Station(
        id: station['id'],
        status: _parseStatus(station['status']),
        lastUpdated: DateTime.parse(station['lastUpdated']),
      );
    }).toList();
  }

  // Helper method to generate mock stations
  List<Station> _getMockStations() {
    return List.generate(
      4,
      (index) => Station(
        id: index + 1,
        status: StationStatus.values[index % 3],
        lastUpdated: DateTime.now(),
      ),
    );
  }

  Future<void> refreshStationStatuses() async {
    // Just call getStationStatuses again
    await getStationStatuses();
  }

  // Helper method to parse status string to enum
  StationStatus _parseStatus(String status) {
    switch (status) {
      case 'available':
        return StationStatus.available;
      case 'inUse':
        return StationStatus.inUse;
      case 'outOfService':
        return StationStatus.outOfService;
      default:
        return StationStatus.outOfService;
    }
  }
}
