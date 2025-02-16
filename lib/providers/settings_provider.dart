import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SettingsProvider with ChangeNotifier {
  static const String _languageKey = 'language_code';
  final SharedPreferences _prefs;
  Locale _locale;

  SettingsProvider(this._prefs)
    : _locale = Locale(_prefs.getString(_languageKey) ?? 'en');

  Locale get locale => _locale;
  bool get isSwedish => _locale.languageCode == 'sv';

  void toggleLanguage() {
    _locale = Locale(_locale.languageCode == 'en' ? 'sv' : 'en');
    _prefs.setString(_languageKey, _locale.languageCode);
    notifyListeners();
  }

  // Translations
  String get available =>
      _locale.languageCode == 'sv' ? 'Tillgänglig' : 'Available';
  String get inUse => _locale.languageCode == 'sv' ? 'I Användning' : 'In Use';
  String get outOfService =>
      _locale.languageCode == 'sv' ? 'Ur Funktion' : 'Out of Service';
  String get chooseServices =>
      _locale.languageCode == 'sv' ? 'Välj Tjänster' : 'Choose Services';
  String get quickWashStatus =>
      _locale.languageCode == 'sv' ? 'Snabbtvätt Status' : 'Quick Wash Status';
  String get settings =>
      _locale.languageCode == 'sv' ? 'Inställningar' : 'Settings';
  String get language => _locale.languageCode == 'sv' ? 'Språk' : 'Language';
  String get darkMode =>
      _locale.languageCode == 'sv' ? 'Mörkt Läge' : 'Dark Mode';
  String get selfServeCarWash =>
      _locale.languageCode == 'sv'
          ? 'Självbetjäning Biltvätt'
          : 'Self-Serve Car Wash';
  String get lastUpdated =>
      _locale.languageCode == 'sv' ? 'Senast uppdaterad' : 'Last updated';
  String get bay => _locale.languageCode == 'sv' ? 'Plats' : 'Bay';
}
