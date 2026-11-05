#!/bin/bash
# Build LAN Share Hub for macOS -> dist/LANShareHub-macOS.dmg
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}

[ -d .venv-mac ] || "$PY" -m venv .venv-mac
.venv-mac/bin/pip install -q --upgrade pip
.venv-mac/bin/pip install -q -r requirements.txt pyinstaller

# .icns from the 1024px master icon
mkdir -p build/icon.iconset
for s in 16 32 128 256 512; do
  sips -z $s $s assets/icon-1024.png --out build/icon.iconset/icon_${s}x${s}.png >/dev/null
  sips -z $((s*2)) $((s*2)) assets/icon-1024.png --out build/icon.iconset/icon_${s}x${s}@2x.png >/dev/null
done
iconutil -c icns build/icon.iconset -o build/icon.icns

.venv-mac/bin/pyinstaller --noconfirm --clean --distpath dist --workpath build/pyi build_tools/lan_share_hub_mac.spec

APP="dist/LAN Share Hub.app"
# Set SIGN_ID="Developer ID Application: ..." to sign for real (then notarize); otherwise ad-hoc sign.
if [ -n "${SIGN_ID:-}" ]; then
  codesign --force --deep --options runtime --timestamp --sign "$SIGN_ID" "$APP"
else
  codesign --force --deep --sign - "$APP"
fi

STAGE=build/dmg
rm -rf "$STAGE" && mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f dist/LANShareHub-macOS.dmg
hdiutil create -volname "LAN Share Hub" -srcfolder "$STAGE" -ov -format UDZO dist/LANShareHub-macOS.dmg >/dev/null
echo "Built dist/LANShareHub-macOS.dmg"
