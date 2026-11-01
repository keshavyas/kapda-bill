#!/usr/bin/env bash
# ==============================================================================
# Kapda Bill Pro - Android APK Build Script (Capacitor)
# ==============================================================================

set -e

echo "🔹 [1/4] Building production web assets..."
python3 build.py

echo "🔹 [2/4] Installing Capacitor dependencies if missing..."
if [ ! -d "node_modules/@capacitor/cli" ]; then
  npm install
fi

echo "🔹 [3/4] Initializing Android platform..."
if [ ! -d "android" ]; then
  npx cap add android
fi

echo "🔹 [4/4] Syncing web assets into Android project..."
npx cap sync android

echo "✅ Android project is ready in ./android!"
echo ""
echo "To build your APK:"
echo "👉 Option A (Command Line Debug APK):"
echo "   cd android && ./gradlew assembleDebug"
echo "   Your APK will be at: android/app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "👉 Option B (Android Studio):"
echo "   npx cap open android"
echo "   Then click Build -> Build Bundle(s) / APK(s) -> Build APK(s)"
