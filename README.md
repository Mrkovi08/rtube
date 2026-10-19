# Rtube

🇬🇧 [English](#english) · 🇭🇺 [Magyar](#magyar)

## English

YouTube search that plays audio only. A GTK4 app for Arch Linux with a
frosted-glass look and a classic Winamp skin, plus a small cava spectrum visualizer.

> The app's interface is in Hungarian.

### Install

```sh
git clone https://github.com/Mrkovi08/rtube.git
cd rtube
makepkg -si
```

Or download the ready-made package from the [Releases](https://github.com/Mrkovi08/rtube/releases) page and run:

```sh
sudo pacman -U rtube-1.2.0-1-any.pkg.tar.zst
```

pacman installs the required dependencies automatically (GTK4, GStreamer, yt-dlp...).
Optional extras: `mpv` (open the video), `cava` (spectrum visualizer).

### Launch

- `rtube` – glass look
- `rtube --winamp` – Winamp skin

Both also appear in your application menu.

### DMS bar widget (optional)

For DankMaterialShell users:

```sh
mkdir -p ~/.config/DankMaterialShell/plugins
cp -r /usr/share/rtube/dms-plugin ~/.config/DankMaterialShell/plugins/rtube
```

### Uninstall

```sh
sudo pacman -R rtube
```

---

## Magyar

YouTube kereső, ami csak a hangot játssza. GTK4 alkalmazás Arch Linuxra,
üveges és klasszikus Winamp kinézettel, kis cava spektrumkijelzővel.

#### Telepítés

```sh
git clone https://github.com/Mrkovi08/rtube.git
cd rtube
makepkg -si
```

Vagy töltsd le a kész csomagot a [Releases](https://github.com/Mrkovi08/rtube/releases) oldalról, és:

```sh
sudo pacman -U rtube-1.2.0-1-any.pkg.tar.zst
```

A pacman magától felrakja a szükséges függőségeket (GTK4, GStreamer, yt-dlp...).
Választható extrák: `mpv` (videó megnyitása), `cava` (spektrum).

### Indítás

- `rtube` – üveges kinézet
- `rtube --winamp` – Winamp kinézet

Mindkettő megtalálható az alkalmazásmenüben is.

### DMS sáv widget (opcionális)

```sh
mkdir -p ~/.config/DankMaterialShell/plugins
cp -r /usr/share/rtube/dms-plugin ~/.config/DankMaterialShell/plugins/rtube
```

### Eltávolítás

```sh
sudo pacman -R rtube
```
