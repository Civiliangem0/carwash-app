import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/station.dart';
import '../widgets/station_card.dart';
import '../providers/settings_provider.dart';
import '../services/api_service.dart';

class StatusScreen extends StatefulWidget {
  const StatusScreen({Key? key}) : super(key: key);

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  late List<Station> stations = [];
  DateTime lastUpdated = DateTime.now();
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _initializeStations();
  }

  Future<void> _initializeStations() async {
    setState(() {
      isLoading = true;
    });

    try {
      // Get the ApiService from the provider
      final apiService = Provider.of<ApiService>(context, listen: false);

      // Fetch stations from the API
      final fetchedStations = await apiService.getStationStatuses();

      setState(() {
        stations = fetchedStations;
        lastUpdated = DateTime.now();
        isLoading = false;
      });
    } catch (e) {
      print('Error fetching stations: $e');
      // Fallback to mock data if API fails
      setState(() {
        stations = List.generate(
          4,
          (index) => Station(
            id: index + 1,
            status: StationStatus.values[index % 3],
            lastUpdated: DateTime.now(),
          ),
        );
        isLoading = false;
      });
    }
  }

  Future<void> _refreshStations() async {
    try {
      final apiService = Provider.of<ApiService>(context, listen: false);
      final fetchedStations = await apiService.getStationStatuses();

      setState(() {
        stations = fetchedStations;
        lastUpdated = DateTime.now();
      });
    } catch (e) {
      print('Error refreshing stations: $e');
      // Show error message to user
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to refresh stations')));
    }
  }

  String _getLastUpdatedText() {
    final difference = DateTime.now().difference(lastUpdated);
    if (difference.inSeconds < 5) {
      return 'Just now';
    } else if (difference.inMinutes < 1) {
      return '${difference.inSeconds} seconds ago';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes} minutes ago';
    } else {
      return '${difference.inHours} hours ago';
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text(settings.quickWashStatus),
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _refreshStations,
        child: Column(
          children: [
            Expanded(
              child:
                  isLoading
                      ? const Center(child: CircularProgressIndicator())
                      : stations.isEmpty
                      ? Center(child: Text('No stations available'))
                      : ListView.builder(
                        physics: const AlwaysScrollableScrollPhysics(),
                        itemCount: stations.length,
                        itemBuilder: (context, index) {
                          return StationCard(station: stations[index]);
                        },
                      ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                '${settings.lastUpdated}: ${_getLastUpdatedText()}',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _refreshStations,
        child: const Icon(Icons.refresh),
      ),
    );
  }
}
