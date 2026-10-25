pkgname=rtube
pkgver=1.5.0
pkgrel=1
pkgdesc="YouTube audio-only search and player (GTK4) with glass, Winamp and modern skins"
arch=('any')
url="https://github.com/Mrkovi08/rtube"
license=('custom')
depends=('python' 'python-gobject' 'gtk4' 'gdk-pixbuf2' 'librsvg' 'pango'
         'gstreamer' 'gst-plugins-base' 'gst-plugins-good' 'gst-libav' 'yt-dlp')
optdepends=('mpv: open the video (🎬 button)'
            'cava: spectrum visualizer in the player'
            'deno: JavaScript runtime for YouTube extraction (otherwise fetched to ~/.local/share/rtube/bin)'
            'dms-shell: DankMaterialShell bar widget')
install=rtube.install
source=('rtube.py' 'rtube.sh' 'rtube.desktop' 'rtube-winamp.desktop' 'rtube-modern.desktop'
        'dms-plugin.json' 'dms-Widget.qml' 'skull.svg' 'io.github.rtube.Rtube.svg')
sha256sums=('fd5423cd6ec81e0722e2314584f9b826b861baf1b1096c2208f4d05680f677e5'
            'f352e9e380a3cd17ae1aaa19e452283e094823e667d45d8cdefb9c25b7f6f4c0'
            'a37d8e11fe77d1c30f7fc163f78b21218c48ea272045ae231e1654181632106e'
            'cd650df56df4d0456d7dbc3fa367fbc331268bf0c3072cca904b4adb95e93a86'
            '0f15e5c4a6574211321d7baa2d60ae1d353853fd57c0d9579bd2224329f253d8'
            'b79f6269b87d79aafb49c3c0909e16824fce5e4df7639d241fabeb20c67dc90f'
            '654b0769a5f889de692cf13f047c63679f29872f75bdb4eb5d221386e8f006e5'
            '55e313fa09821003158793e7eef2138e767a7d83e6f6f6d000f5a3e007969f62'
            '93cbb2b12d7e9b0018558ea2dd0d4563ba539f705b6d715e187c6ba768eb3f07')

package() {
  install -Dm644 rtube.py "$pkgdir/usr/share/rtube/rtube.py"
  install -Dm755 rtube.sh "$pkgdir/usr/bin/rtube"
  install -Dm644 rtube.desktop "$pkgdir/usr/share/applications/rtube.desktop"
  install -Dm644 rtube-winamp.desktop "$pkgdir/usr/share/applications/rtube-winamp.desktop"
  install -Dm644 rtube-modern.desktop "$pkgdir/usr/share/applications/rtube-modern.desktop"
  install -Dm644 dms-plugin.json "$pkgdir/usr/share/rtube/dms-plugin/plugin.json"
  install -Dm644 dms-Widget.qml "$pkgdir/usr/share/rtube/dms-plugin/Widget.qml"
  install -Dm644 skull.svg "$pkgdir/usr/share/rtube/dms-plugin/skull.svg"
  install -Dm644 io.github.rtube.Rtube.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/io.github.rtube.Rtube.svg"
}
