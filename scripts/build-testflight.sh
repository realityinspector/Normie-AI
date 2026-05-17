#!/usr/bin/env bash
# Build NORMALIZER iOS for TestFlight: run UI tests on simulator, then archive
# + export an .ipa ready for `xcrun altool --upload-app`.
#
# Usage:
#   scripts/build-testflight.sh              # test + archive + export
#   scripts/build-testflight.sh --test-only  # just the UI tests
#   scripts/build-testflight.sh --upload     # also upload to TestFlight
#                                            #   needs APPLE_ID + APPLE_APP_PASSWORD env
#
# Prerequisites:
# - Xcode installed and CLI tools selected (`xcode-select -p`)
# - A valid signing identity + provisioning profile for com.normalaizer.app
# - For --upload: an app-specific password from appleid.apple.com

set -euo pipefail

cd "$(dirname "$0")/.."
IOS_DIR="ios/NORMALIZER"
PROJECT="$IOS_DIR/NORMALIZER.xcodeproj"
SCHEME="NORMALIZER"
SIMULATOR="${SIMULATOR:-iPhone 16}"
BUILD_DIR="${BUILD_DIR:-build}"
ARCHIVE_PATH="$BUILD_DIR/NORMALIZER.xcarchive"
EXPORT_PATH="$BUILD_DIR/export"
EXPORT_OPTIONS="$BUILD_DIR/ExportOptions.plist"

TEST_ONLY=0
DO_UPLOAD=0
for arg in "$@"; do
  case "$arg" in
    --test-only) TEST_ONLY=1 ;;
    --upload) DO_UPLOAD=1 ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

if ! command -v xcodebuild >/dev/null; then
  echo "xcodebuild not found — install Xcode and run xcode-select --install" >&2
  exit 1
fi

mkdir -p "$BUILD_DIR"

echo "==> Running XCUITest DemoFlowUITests on $SIMULATOR"
xcodebuild test \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -destination "platform=iOS Simulator,name=$SIMULATOR" \
  -only-testing:NORMALIZERUITests/DemoFlowUITests \
  | tee "$BUILD_DIR/test.log" \
  | xcpretty 2>/dev/null || true

if grep -q "\\*\\* TEST FAILED \\*\\*" "$BUILD_DIR/test.log"; then
  echo "TESTS FAILED — see $BUILD_DIR/test.log" >&2
  exit 1
fi
echo "==> Tests passed."

if [ "$TEST_ONLY" -eq 1 ]; then
  exit 0
fi

if [ -z "${DEVELOPMENT_TEAM:-}" ]; then
  echo "DEVELOPMENT_TEAM env var not set — required for archive signing." >&2
  echo "Find your Team ID at https://developer.apple.com/account → Membership." >&2
  echo "Then re-run: DEVELOPMENT_TEAM=ABC1234567 scripts/build-testflight.sh" >&2
  exit 1
fi

echo "==> Archiving for Generic iOS Device (team $DEVELOPMENT_TEAM)"
xcodebuild archive \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -configuration Release \
  -destination "generic/platform=iOS" \
  -archivePath "$ARCHIVE_PATH" \
  DEVELOPMENT_TEAM="$DEVELOPMENT_TEAM" \
  | tee "$BUILD_DIR/archive.log" \
  | xcpretty 2>/dev/null || true

if [ ! -d "$ARCHIVE_PATH" ]; then
  echo "Archive failed — see $BUILD_DIR/archive.log" >&2
  exit 1
fi

cat >"$EXPORT_OPTIONS" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key><string>app-store</string>
  <key>signingStyle</key><string>automatic</string>
  <key>teamID</key><string>$DEVELOPMENT_TEAM</string>
  <key>uploadBitcode</key><false/>
  <key>uploadSymbols</key><true/>
</dict>
</plist>
PLIST

echo "==> Exporting .ipa"
xcodebuild -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_PATH" \
  -exportOptionsPlist "$EXPORT_OPTIONS" \
  | tee "$BUILD_DIR/export.log" \
  | xcpretty 2>/dev/null || true

IPA=$(find "$EXPORT_PATH" -name "*.ipa" -print -quit || true)
if [ -z "$IPA" ]; then
  echo "Export did not produce an .ipa — see $BUILD_DIR/export.log" >&2
  exit 1
fi
echo "==> .ipa ready: $IPA"

if [ "$DO_UPLOAD" -eq 1 ]; then
  : "${APPLE_ID:?APPLE_ID not set}"
  : "${APPLE_APP_PASSWORD:?APPLE_APP_PASSWORD not set (app-specific password)}"
  echo "==> Uploading to TestFlight"
  xcrun altool --upload-app -f "$IPA" -t ios \
    -u "$APPLE_ID" -p "$APPLE_APP_PASSWORD"
fi

echo "==> Done."
