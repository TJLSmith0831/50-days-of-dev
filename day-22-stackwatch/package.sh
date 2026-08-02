#!/usr/bin/env bash
# Build StackWatch.app and install it to /Applications.
#
#   ./package.sh            build + install to /Applications
#   ./package.sh --no-install   build the bundle into ./dist only
#
# The icon is optional: without assets/icon.png the bundle still builds and runs, it just
# gets the generic app icon. Drop a square PNG (1024x1024 ideally) there and re-run.
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="StackWatch"
BUNDLE_ID="com.tjlsmith.stackwatch"
VERSION="1.0.0"
DIST="dist"
APP="$DIST/$APP_NAME.app"

echo "==> building release binary"
cargo build --release --bin stackwatch

echo "==> assembling $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "target/release/stackwatch" "$APP/Contents/MacOS/$APP_NAME"

if [[ -f assets/icon.png ]]; then
  echo "==> building icns from assets/icon.png"
  ICONSET="$DIST/$APP_NAME.iconset"
  rm -rf "$ICONSET"; mkdir -p "$ICONSET"
  # The sizes Finder, the Dock, and Spotlight each pull from. Missing @2x variants make
  # the icon render blurry on a Retina display rather than not at all, which is worse —
  # it looks like a broken app instead of an unfinished one.
  for size in 16 32 128 256 512; do
    sips -z $size $size assets/icon.png --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    sips -z $((size*2)) $((size*2)) assets/icon.png \
      --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/$APP_NAME.icns"
  rm -rf "$ICONSET"
  ICON_ENTRY="<key>CFBundleIconFile</key><string>$APP_NAME</string>"
else
  echo "==> no assets/icon.png — bundling without a custom icon"
  ICON_ENTRY=""
fi

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key><string>$APP_NAME</string>
    <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
    <key>CFBundleName</key><string>$APP_NAME</string>
    <key>CFBundleDisplayName</key><string>$APP_NAME</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>CFBundleVersion</key><string>$VERSION</string>
    $ICON_ENTRY
    <key>LSMinimumSystemVersion</key><string>12.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <!-- No Dock tile and no app-switcher entry: StackWatch lives in the notch. This
         matches the NSApplicationActivationPolicy::Accessory the app sets at startup;
         setting only one of the two gives a Dock icon that flickers in and out. -->
    <key>LSUIElement</key><true/>
</dict>
</plist>
PLIST

# Strip extended attributes first. Finder/iCloud leave `com.apple.provenance` and friends
# on copied files, and codesign refuses to sign a bundle carrying them:
# "resource fork, Finder information, or similar detritus not allowed".
xattr -cr "$APP"

# Signing identity. Ad-hoc (`-`) works, but its cdhash changes on every build — and macOS
# keys TCC permissions (Screen Recording, Desktop/Documents access) to that hash. So an
# ad-hoc app has to be re-approved after *every* rebuild.
#
# Set CODESIGN_ID to a stable self-signed identity and the grants persist:
#   Keychain Access → Certificate Assistant → Create a Certificate…
#     name: StackWatch Dev · type: Code Signing · self-signed
#   CODESIGN_ID="StackWatch Dev" ./package.sh
CODESIGN_ID="${CODESIGN_ID:--}"
if [[ "$CODESIGN_ID" == "-" ]]; then
  echo "==> ad-hoc signing (permissions reset on each rebuild — see CODESIGN_ID above)"
else
  echo "==> signing as '$CODESIGN_ID'"
fi
codesign --force --deep --sign "$CODESIGN_ID" "$APP"

if [[ "${1:-}" == "--no-install" ]]; then
  echo "==> built $APP (not installed)"
  exit 0
fi

echo "==> installing to /Applications"
rm -rf "/Applications/$APP_NAME.app"
cp -R "$APP" "/Applications/$APP_NAME.app"
echo "==> done: /Applications/$APP_NAME.app"
