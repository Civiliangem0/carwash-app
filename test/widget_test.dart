// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:carwash_app/main.dart';
import 'package:carwash_app/services/api_service.dart';

void main() {
  testWidgets('App renders successfully', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final apiService = ApiService();

    // Build our app and trigger a frame.
    await tester.pumpWidget(CarWashApp(prefs: prefs, apiService: apiService));

    // Verify that the login screen is shown (since we're not authenticated)
    expect(find.text('Login'), findsOneWidget);
  });
}
