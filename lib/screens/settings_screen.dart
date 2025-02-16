import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/settings_provider.dart';
import '../providers/theme_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final theme = context.watch<ThemeProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text(settings.settings),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        children: [
          ListTile(
            title: Text(settings.language),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(settings.isSwedish ? 'Svenska' : 'English'),
                const SizedBox(width: 8),
                const Icon(Icons.language),
              ],
            ),
            onTap: settings.toggleLanguage,
          ),
          const Divider(),
          SwitchListTile(
            title: Text(settings.darkMode),
            value: theme.isDarkMode,
            onChanged: (_) => theme.toggleTheme(),
            secondary: Icon(
              theme.isDarkMode ? Icons.dark_mode : Icons.light_mode,
            ),
          ),
        ],
      ),
    );
  }
}
