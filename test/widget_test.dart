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

void main() {
  testWidgets('App renders successfully', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    // Build our app and trigger a frame.
    await tester.pumpWidget(CarWashApp(prefs: prefs));

    // Verify that the services screen is shown
    expect(find.text('Choose Services'), findsOneWidget);
    expect(find.text('Self-Serve Car Wash'), findsOneWidget);
  });
}
