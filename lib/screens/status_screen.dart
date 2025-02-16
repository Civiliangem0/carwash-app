import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/station.dart';
import '../widgets/station_card.dart';
import '../providers/settings_provider.dart';

class StatusScreen extends StatefulWidget {
  const StatusScreen({Key? key}) : super(key: key);

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  late List<Station> stations;
  DateTime lastUpdated = DateTime.now();

  @override
  void initState() {
    super.initState();
    _initializeStations();
  }

  void _initializeStations() {
    stations = List.generate(
      4,
      (index) => Station(
        id: index + 1,
        status: StationStatus.values[index % 3],
        lastUpdated: DateTime.now(),
      ),
    );
  }

  Future<void> _refreshStations() async {
    // Simulate network delay
    await Future.delayed(const Duration(seconds: 1));

    setState(() {
      _initializeStations();
      lastUpdated = DateTime.now();
    });
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
              child: ListView.builder(
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
