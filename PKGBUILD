pkgname=rtube
pkgver=1.7.0
pkgrel=1
pkgdesc="YouTube audio-only search and player (GTK4) with a modern look (dark / light / system) and a compact mini-player"
arch=('any')
url="https://github.com/Mrkovi08/rtube"
license=('MIT')
depends=('python' 'python-gobject' 'gtk4' 'gdk-pixbuf2' 'librsvg' 'pango'
         'gstreamer' 'gst-plugins-base' 'gst-plugins-good' 'gst-libav' 'yt-dlp')
optdepends=('mpv: open the video (🎬 button)'
            'deno: JavaScript runtime for YouTube extraction (otherwise fetched to ~/.local/share/rtube/bin)'
            'dms-shell: DankMaterialShell bar widget')
install=rtube.install
source=('LICENSE' 'rtube.py' 'rtube.sh' 'rtube.desktop'
        'dms-plugin.json' 'dms-Widget.qml' 'skull.svg' 'io.github.rtube.Rtube.svg')
sha256sums=('6af569d9d2f0c51334014f743b147e4b25495394095208322d3f902438cdeee5'
            '76a72ca07223a824ccf4809495e720f200dd1efbad20d478667610ccf62ed95e'
            '20d03116b590cc42e075f585e8636f1dda5ce0c4905fbe725109ea7ea6380940'
            'a37d8e11fe77d1c30f7fc163f78b21218c48ea272045ae231e1654181632106e'
            'b79f6269b87d79aafb49c3c0909e16824fce5e4df7639d241fabeb20c67dc90f'
            '654b0769a5f889de692cf13f047c63679f29872f75bdb4eb5d221386e8f006e5'
            '55e313fa09821003158793e7eef2138e767a7d83e6f6f6d000f5a3e007969f62'
            '93cbb2b12d7e9b0018558ea2dd0d4563ba539f705b6d715e187c6ba768eb3f07')

package() {
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 rtube.py "$pkgdir/usr/share/rtube/rtube.py"
  install -Dm755 rtube.sh "$pkgdir/usr/bin/rtube"
  install -Dm644 rtube.desktop "$pkgdir/usr/share/applications/rtube.desktop"
  install -Dm644 dms-plugin.json "$pkgdir/usr/share/rtube/dms-plugin/plugin.json"
  install -Dm644 dms-Widget.qml "$pkgdir/usr/share/rtube/dms-plugin/Widget.qml"
  install -Dm644 skull.svg "$pkgdir/usr/share/rtube/dms-plugin/skull.svg"
  install -Dm644 io.github.rtube.Rtube.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/io.github.rtube.Rtube.svg"
}
