import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/services_screen.dart';
import 'screens/login_screen.dart';
import 'providers/settings_provider.dart';
import 'providers/theme_provider.dart';
import 'providers/auth_provider.dart';
import 'services/api_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize shared preferences
  final prefs = await SharedPreferences.getInstance();

  // Initialize API service
  final apiService = ApiService();
  await apiService.init();

  runApp(CarWashApp(prefs: prefs, apiService: apiService));
}

class CarWashApp extends StatelessWidget {
  final SharedPreferences prefs;
  final ApiService apiService;

  const CarWashApp({Key? key, required this.prefs, required this.apiService})
    : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider(prefs)),
        ChangeNotifierProvider(create: (_) => SettingsProvider(prefs)),
        ChangeNotifierProvider(create: (_) => AuthProvider(apiService)),
        Provider.value(value: apiService),
      ],
      child: Consumer3<ThemeProvider, SettingsProvider, AuthProvider>(
        builder:
            (context, theme, settings, auth, _) => MaterialApp(
              title: 'Maria Carwash',
              theme: theme.theme,
              home:
                  auth.isAuthenticated
                      ? const ServicesScreen()
                      : const LoginScreen(),
              debugShowCheckedModeBanner: false,
            ),
      ),
    );
  }
}
