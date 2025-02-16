import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/station.dart';
import '../providers/settings_provider.dart';

class StationCard extends StatelessWidget {
  final Station station;

  const StationCard({Key? key, required this.station}) : super(key: key);

  Color _getStatusColor() {
    switch (station.status) {
      case StationStatus.available:
        return Colors.green.shade200;
      case StationStatus.inUse:
        return Colors.red.shade200;
      case StationStatus.outOfService:
        return Colors.yellow.shade200;
    }
  }

  IconData _getStatusIcon() {
    switch (station.status) {
      case StationStatus.available:
        return Icons.check_circle_outline;
      case StationStatus.inUse:
        return Icons.error_outline;
      case StationStatus.outOfService:
        return Icons.access_time;
    }
  }

  String _getStatusText(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    switch (station.status) {
      case StationStatus.available:
        return settings.available;
      case StationStatus.inUse:
        return settings.inUse;
      case StationStatus.outOfService:
        return settings.outOfService;
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      decoration: BoxDecoration(
        color: _getStatusColor(),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${settings.bay} ${station.id}',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _getStatusText(context),
                    style: TextStyle(
                      color:
                          station.status == StationStatus.inUse
                              ? Colors.red.shade700
                              : station.status == StationStatus.outOfService
                              ? Colors.yellow.shade900
                              : Colors.green.shade700,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              _getStatusIcon(),
              size: 24,
              color:
                  station.status == StationStatus.inUse
                      ? Colors.red.shade700
                      : station.status == StationStatus.outOfService
                      ? Colors.yellow.shade900
                      : Colors.green.shade700,
            ),
          ],
        ),
      ),
    );
  }
}
