#!/bin/sh
# Build the Ubuntu / Linux Mint package: packaging/deb/build-deb.sh [outdir]
# Needs only dpkg-deb (no root: --root-owner-group). Output: rtube_<ver>-<rel>_all.deb
set -eu
VERSION=1.5.0
RELEASE=1
TOP=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:-$TOP/dist}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
R=$WORK/rtube

install -Dm644 "$TOP/rtube.py"                 "$R/usr/share/rtube/rtube.py"
install -Dm755 "$TOP/rtube.sh"                 "$R/usr/bin/rtube"
install -Dm644 "$TOP/rtube.desktop"            "$R/usr/share/applications/rtube.desktop"
install -Dm644 "$TOP/rtube-winamp.desktop"     "$R/usr/share/applications/rtube-winamp.desktop"
install -Dm644 "$TOP/rtube-modern.desktop"     "$R/usr/share/applications/rtube-modern.desktop"
install -Dm644 "$TOP/io.github.rtube.Rtube.svg" "$R/usr/share/icons/hicolor/scalable/apps/io.github.rtube.Rtube.svg"
install -Dm644 "$TOP/dms-plugin.json"          "$R/usr/share/rtube/dms-plugin/plugin.json"
install -Dm644 "$TOP/dms-Widget.qml"           "$R/usr/share/rtube/dms-plugin/Widget.qml"
install -Dm644 "$TOP/skull.svg"                "$R/usr/share/rtube/dms-plugin/skull.svg"

DOC=$R/usr/share/doc/rtube
install -d "$DOC"
cat > "$DOC/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: rtube
Source: https://github.com/Mrkovi08/rtube

Files: *
Copyright: Mrkovi08
License: custom
 All rights reserved by the author; see https://github.com/Mrkovi08/rtube
EOF
DATE=$(date -R -d "@${SOURCE_DATE_EPOCH:-$(git -C "$TOP" log -1 --format=%ct 2>/dev/null || date +%s)}")
cat > "$WORK/changelog" <<EOF
rtube ($VERSION-$RELEASE) noble; urgency=medium

  * New modern skin (rtube --modern, "Rtube (Modern)" menu entry) with a
    compact mini-player view (list toggle, "Up next" strip); the view is
    remembered in ~/.config/rtube/state.json.

 -- Mrkovi08 <Mrkovi08@users.noreply.github.com>  $DATE
EOF
gzip -9n -c "$WORK/changelog" > "$DOC/changelog.gz"

SIZE=$(du -sk "$R/usr" | cut -f1)
install -d "$R/DEBIAN"
cat > "$R/DEBIAN/control" <<EOF
Package: rtube
Version: $VERSION-$RELEASE
Architecture: all
Maintainer: Mrkovi08 <Mrkovi08@users.noreply.github.com>
Installed-Size: $SIZE
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0, gir1.2-gstreamer-1.0, gir1.2-gdkpixbuf-2.0, gir1.2-pango-1.0, gir1.2-glib-2.0, librsvg2-common, gstreamer1.0-plugins-base, gstreamer1.0-plugins-good, gstreamer1.0-libav, fonts-dejavu-core, ca-certificates
Recommends: mpv, cava
Suggests: yt-dlp
Section: sound
Priority: optional
Homepage: https://github.com/Mrkovi08/rtube
Description: YouTube audio-only search and player (GTK4)
 Rtube searches YouTube and plays only the audio, with a glass look, a
 classic Winamp skin (rtube --winamp) and a modern dark skin with a compact
 mini-player (rtube --modern), plus an optional cava spectrum visualizer.
 The UI is Hungarian on Hungarian locales, English otherwise.
 .
 A current yt-dlp and, if no suitable node/deno is installed, deno are
 downloaded on first run into ~/.local/share/rtube/bin (official GitHub
 releases, SHA-256 verified), because distribution yt-dlp is usually too
 old for YouTube.
EOF
# desktop database / icon cache: handled by dpkg triggers (desktop-file-utils, hicolor-icon-theme)
(cd "$R" && find usr -type f -exec md5sum {} + | sort -k2) > "$R/DEBIAN/md5sums"

mkdir -p "$OUT"
DEB=$OUT/rtube_${VERSION}-${RELEASE}_all.deb
dpkg-deb --root-owner-group -Zxz --build "$R" "$DEB" >/dev/null
echo "$DEB"
