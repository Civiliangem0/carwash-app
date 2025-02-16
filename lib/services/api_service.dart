import '../models/station.dart';

class ApiService {
  // Singleton pattern
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  // TODO: Replace with actual API calls
  Future<List<Station>> getStationStatuses() async {
    // Simulate network delay
    await Future.delayed(const Duration(seconds: 1));
    
    // Return mock data
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
    // TODO: Implement actual refresh logic
    await Future.delayed(const Duration(seconds: 1));
  }
}
