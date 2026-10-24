pkgname=rtube
pkgver=1.4.0
pkgrel=1
pkgdesc="YouTube audio-only search and player (GTK4) with glass and Winamp skins"
arch=('any')
url="https://github.com/Mrkovi08/rtube"
license=('custom')
depends=('python' 'python-gobject' 'gtk4' 'gdk-pixbuf2' 'pango'
         'gstreamer' 'gst-plugins-base' 'gst-plugins-good' 'gst-libav' 'yt-dlp')
optdepends=('mpv: open the video (🎬 button)'
            'cava: spectrum visualizer in the player'
            'deno: JavaScript runtime for YouTube extraction (otherwise fetched to ~/.local/share/rtube/bin)'
            'dms-shell: DankMaterialShell bar widget')
install=rtube.install
source=('rtube.py' 'rtube.sh' 'rtube.desktop' 'rtube-winamp.desktop'
        'dms-plugin.json' 'dms-Widget.qml' 'skull.svg' 'io.github.rtube.Rtube.svg')
sha256sums=('6e932068424cf179c0e87e06ff277425aa3f8b94b609e73266c5c7e9ddd42d3a'
            '821080c2139b001e4f8968bf8fc3920288a5888cbcd9524120226f5f3e0374cc'
            'a37d8e11fe77d1c30f7fc163f78b21218c48ea272045ae231e1654181632106e'
            'cd650df56df4d0456d7dbc3fa367fbc331268bf0c3072cca904b4adb95e93a86'
            '2c0d6bbdf74ef4eab4ff629cc4c9bd2e724f36bc8257812fb1387b05400ff32a'
            '654b0769a5f889de692cf13f047c63679f29872f75bdb4eb5d221386e8f006e5'
            '55e313fa09821003158793e7eef2138e767a7d83e6f6f6d000f5a3e007969f62'
            '93cbb2b12d7e9b0018558ea2dd0d4563ba539f705b6d715e187c6ba768eb3f07')

package() {
  install -Dm644 rtube.py "$pkgdir/usr/share/rtube/rtube.py"
  install -Dm755 rtube.sh "$pkgdir/usr/bin/rtube"
  install -Dm644 rtube.desktop "$pkgdir/usr/share/applications/rtube.desktop"
  install -Dm644 rtube-winamp.desktop "$pkgdir/usr/share/applications/rtube-winamp.desktop"
  install -Dm644 dms-plugin.json "$pkgdir/usr/share/rtube/dms-plugin/plugin.json"
  install -Dm644 dms-Widget.qml "$pkgdir/usr/share/rtube/dms-plugin/Widget.qml"
  install -Dm644 skull.svg "$pkgdir/usr/share/rtube/dms-plugin/skull.svg"
  install -Dm644 io.github.rtube.Rtube.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/io.github.rtube.Rtube.svg"
}
