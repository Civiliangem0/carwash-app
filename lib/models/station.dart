enum StationStatus {
  available,
  inUse,
  outOfService,
}

class Station {
  final int id;
  final StationStatus status;
  final DateTime lastUpdated;

  Station({
    required this.id,
    required this.status,
    required this.lastUpdated,
  });

  // Helper method to get color based on status
  static String getStatusText(StationStatus status) {
    switch (status) {
      case StationStatus.available:
        return 'Available';
      case StationStatus.inUse:
        return 'In Use';
      case StationStatus.outOfService:
        return 'Out of Service';
    }
  }
}
