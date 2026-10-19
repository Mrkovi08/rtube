pkgname=rtube
pkgver=1.2.0
pkgrel=1
pkgdesc="YouTube audio-only search and player (GTK4) with glass and Winamp skins"
arch=('any')
url="https://github.com/Mrkovi08/rtube"
license=('custom')
depends=('python' 'python-gobject' 'gtk4' 'gdk-pixbuf2' 'pango'
         'gstreamer' 'gst-plugins-base' 'gst-plugins-good' 'gst-libav' 'yt-dlp')
optdepends=('mpv: open the video (🎬 button)'
            'cava: spectrum visualizer in the player'
            'dms-shell: DankMaterialShell bar widget')
install=rtube.install
source=('rtube.py' 'rtube.sh' 'rtube.desktop' 'rtube-winamp.desktop'
        'dms-plugin.json' 'dms-Widget.qml' 'skull.svg')
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  install -Dm644 rtube.py "$pkgdir/usr/share/rtube/rtube.py"
  install -Dm755 rtube.sh "$pkgdir/usr/bin/rtube"
  install -Dm644 rtube.desktop "$pkgdir/usr/share/applications/rtube.desktop"
  install -Dm644 rtube-winamp.desktop "$pkgdir/usr/share/applications/rtube-winamp.desktop"
  install -Dm644 dms-plugin.json "$pkgdir/usr/share/rtube/dms-plugin/plugin.json"
  install -Dm644 dms-Widget.qml "$pkgdir/usr/share/rtube/dms-plugin/Widget.qml"
  install -Dm644 skull.svg "$pkgdir/usr/share/rtube/dms-plugin/skull.svg"
}
