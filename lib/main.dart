import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/services_screen.dart';
import 'providers/settings_provider.dart';
import 'providers/theme_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  runApp(CarWashApp(prefs: prefs));
}

class CarWashApp extends StatelessWidget {
  final SharedPreferences prefs;

  const CarWashApp({Key? key, required this.prefs}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider(prefs)),
        ChangeNotifierProvider(create: (_) => SettingsProvider(prefs)),
      ],
      child: Consumer2<ThemeProvider, SettingsProvider>(
        builder:
            (context, theme, settings, _) => MaterialApp(
              title: 'Maria Carwash',
              theme: theme.theme,
              home: const ServicesScreen(),
              debugShowCheckedModeBanner: false,
            ),
      ),
    );
  }
}
