# Rtube

YouTube kereső, ami csak a hangot játssza. GTK4 alkalmazás Arch Linuxra,
üveges és klasszikus Winamp kinézettel, kis cava spektrumkijelzővel.

## Telepítés

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

## Indítás

- `rtube` – üveges kinézet
- `rtube --winamp` – Winamp kinézet

Mindkettő megtalálható az alkalmazásmenüben is.

## DMS sáv widget (opcionális)

```sh
mkdir -p ~/.config/DankMaterialShell/plugins
cp -r /usr/share/rtube/dms-plugin ~/.config/DankMaterialShell/plugins/rtube
```

## Eltávolítás

```sh
sudo pacman -R rtube
```
