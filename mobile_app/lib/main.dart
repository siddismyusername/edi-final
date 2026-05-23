import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const ETASyncApp());
}

/// Main application widget for ETA-Sync
class ETASyncApp extends StatelessWidget {
  const ETASyncApp({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF006A6A),
      brightness: Brightness.light,
    );

    return MaterialApp(
      title: 'ETA-Sync Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: colorScheme,
        scaffoldBackgroundColor: const Color(0xFFF7FAFA),
        appBarTheme: AppBarTheme(
          centerTitle: true,
          elevation: 0,
          scrolledUnderElevation: 0,
          backgroundColor: colorScheme.surface,
          foregroundColor: colorScheme.onSurface,
        ),
        cardTheme: CardThemeData(
          elevation: 0,
          color: colorScheme.surface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
            side: BorderSide(
              color: colorScheme.outlineVariant.withValues(alpha: 0.7),
            ),
          ),
        ),
        textTheme: ThemeData.light().textTheme.copyWith(
              displaySmall: const TextStyle(fontWeight: FontWeight.w700),
              headlineSmall: const TextStyle(fontWeight: FontWeight.w700),
              titleLarge: const TextStyle(fontWeight: FontWeight.w700),
              titleMedium: const TextStyle(fontWeight: FontWeight.w600),
            ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            elevation: 0,
            minimumSize: const Size(double.infinity, 52),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            textStyle: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size(double.infinity, 52),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            textStyle: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: colorScheme.outlineVariant),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: colorScheme.outlineVariant),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: colorScheme.primary, width: 1.8),
          ),
          filled: true,
          fillColor: colorScheme.surfaceContainerLowest,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
        ),
      ),
      home: const HomeScreen(),
    );
  }
}
