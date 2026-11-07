# Rtube

🇬🇧 [English](#english) · 🇭🇺 [Magyar](#magyar)

## English

| Full view | Compact mini-player |
|:---:|:---:|
| ![Rtube](screenshots/modern.png) | ![Rtube compact view](screenshots/modern-compact.png) |

YouTube search that plays audio only. A GTK4 app for Arch Linux and Ubuntu / Linux Mint with a
clean, modern dark look and a compact mini-player.

> The app follows the system language (Hungarian or English). Force it with
> `RTUBE_LANG=en` or `RTUBE_LANG=hu`, e.g. `RTUBE_LANG=en rtube`.

### Install

#### Arch Linux

```sh
git clone https://github.com/Mrkovi08/rtube.git
cd rtube
makepkg -si
```

Or download the ready-made package from the [Releases](https://github.com/Mrkovi08/rtube/releases) page and run:

```sh
cd /tmp && curl -LO https://github.com/Mrkovi08/rtube/releases/download/v1.6.1/rtube-1.6.1-1-any.pkg.tar.zst && sudo pacman -U ./rtube-1.6.1-1-any.pkg.tar.zst
```

pacman installs the required dependencies automatically (GTK4, GStreamer, yt-dlp...).
Optional extra: `mpv` (open the video).

#### Ubuntu / Linux Mint

Download `rtube_1.6.1-1_all.deb` from the [Releases](https://github.com/Mrkovi08/rtube/releases) page,
then double-click it (Software Manager / App Center) or run:

```sh
cd /tmp && wget https://github.com/Mrkovi08/rtube/releases/download/v1.6.1/rtube_1.6.1-1_all.deb && sudo apt install ./rtube_1.6.1-1_all.deb
```

apt installs everything it needs automatically: Python GTK4 bindings, GStreamer
(with `gstreamer1.0-libav` for YouTube audio), and the recommended `mpv`.
Tested on Ubuntu 24.04 / Linux Mint 22.

The yt-dlp in the Ubuntu archive is too old for YouTube, so on first launch Rtube
downloads the latest standalone **yt-dlp** and, if no new enough Node.js (20+) is
installed, **deno** (YouTube's JavaScript runtime) into `~/.local/share/rtube/bin`.
This happens in your user account, without sudo; the status line shows the progress,
and yt-dlp is kept up to date automatically. Your own `~/.config/yt-dlp/config`
(e.g. cookies) is respected. Check the tools any time with `rtube --check-tools`.

### Usage

Start it with `rtube` or from your application menu ("Rtube"). A large "Now playing" card sits next to the results / favorites list.

- **Compact mini-player:** the small button at the top right switches to a narrow player-only view
  with an "Up next" strip at the bottom (click it to play the next song). The **List** button
  brings the full view back. Rtube remembers the last view (`~/.config/rtube/state.json`).
- Searching from the compact view switches back to the full list automatically.
- The 🎬 (camera) button opens the video separately in **mpv**.
- **Playback problems:** Rtube retries automatically with another YouTube method. If the song still fails, a **Repair** button appears next to the status line: it updates yt-dlp and the JS runtime, then retries the song.
- On Hyprland floating windows Rtube also resizes the window via `hyprctl`; on other desktops
  the normal GTK window sizing is used.

### DMS bar widget (optional)

For DankMaterialShell users:

```sh
mkdir -p ~/.config/DankMaterialShell/plugins
cp -r /usr/share/rtube/dms-plugin ~/.config/DankMaterialShell/plugins/rtube
```

### Uninstall

```sh
sudo pacman -R rtube      # Arch
sudo apt remove rtube     # Ubuntu / Linux Mint
rm -rf ~/.local/share/rtube   # optional: downloaded yt-dlp / deno
```

### License

[MIT](LICENSE)

---

## Magyar

| Teljes nézet | Kompakt mini-lejátszó |
|:---:|:---:|
| ![Rtube](screenshots/modern.png) | ![Rtube kompakt nézet](screenshots/modern-compact.png) |

YouTube kereső, ami csak a hangot játssza. GTK4 alkalmazás Arch Linuxra és Ubuntu / Linux Mintre,
letisztult, modern sötét kinézettel és kompakt mini-lejátszóval.

> Az alkalmazás a rendszer nyelvét követi (magyar vagy angol). Kényszeríteni a
> `RTUBE_LANG=en` vagy `RTUBE_LANG=hu` változóval lehet, pl. `RTUBE_LANG=hu rtube`.

### Telepítés

#### Arch Linux

```sh
git clone https://github.com/Mrkovi08/rtube.git
cd rtube
makepkg -si
```

Vagy töltsd le a kész csomagot a [Releases](https://github.com/Mrkovi08/rtube/releases) oldalról, és:

```sh
cd /tmp && curl -LO https://github.com/Mrkovi08/rtube/releases/download/v1.6.1/rtube-1.6.1-1-any.pkg.tar.zst && sudo pacman -U ./rtube-1.6.1-1-any.pkg.tar.zst
```

A pacman magától felrakja a szükséges függőségeket (GTK4, GStreamer, yt-dlp...).
Választható extra: `mpv` (videó megnyitása).

#### Ubuntu / Linux Mint

Töltsd le az `rtube_1.6.1-1_all.deb` fájlt a [Releases](https://github.com/Mrkovi08/rtube/releases) oldalról,
majd kattints rá duplán (Szoftverkezelő / App Center), vagy:

```sh
cd /tmp && wget https://github.com/Mrkovi08/rtube/releases/download/v1.6.1/rtube_1.6.1-1_all.deb && sudo apt install ./rtube_1.6.1-1_all.deb
```

Az apt magától felrak mindent, ami kell: a Python GTK4 csatolókat, a GStreamert
(a YouTube hanghoz szükséges `gstreamer1.0-libav`-val), és az ajánlott `mpv`-t.
Tesztelve: Ubuntu 24.04 / Linux Mint 22.

Az Ubuntu tárolójában lévő yt-dlp túl régi a YouTube-hoz, ezért az első indításkor
az Rtube letölti a legfrissebb önálló **yt-dlp**-t, és ha nincs elég új Node.js (20+),
a **deno**-t is (a YouTube JavaScript futtatókörnyezete) a `~/.local/share/rtube/bin` mappába.
Ez a saját felhasználói fiókodban történik, sudo nélkül; az állapotsor mutatja a haladást,
és a yt-dlp-t magától frissen tartja. A saját `~/.config/yt-dlp/config` beállításaidat
(pl. sütik) figyelembe veszi. Ellenőrzés bármikor: `rtube --check-tools`.

### Használat

Indítás: `rtube` vagy az alkalmazásmenü („Rtube”). A találatok / kedvencek listája mellett egy nagy „Most szól” kártya van.

- **Kompakt mini-lejátszó:** a jobb felső kis gomb keskeny, csak lejátszós nézetre vált, alul egy
  „Következő” sávval (rákattintva a következő szám indul). A **Lista** gomb visszahozza a teljes
  nézetet. Az Rtube megjegyzi az utolsó nézetet (`~/.config/rtube/state.json`).
- Ha a kompakt nézetben keresel, magától visszavált a teljes listára.
- A 🎬 (kamera) gomb külön, **mpv**-ben nyitja meg a videót.
- **Lejátszási hiba:** az Rtube magától újrapróbálja egy másik YouTube-módszerrel. Ha a szám még így sem szól, a státuszsor mellett megjelenik a **Javítás** gomb: frissíti a yt-dlp-t és a JS futtatókörnyezetet, majd újrapróbálja a számot.
- Hyprlandon a lebegő ablakot `hyprctl`-lel is átméretezi; más asztali környezetben a
  szokásos GTK ablakméretezés működik.

### DMS sáv widget (opcionális)

```sh
mkdir -p ~/.config/DankMaterialShell/plugins
cp -r /usr/share/rtube/dms-plugin ~/.config/DankMaterialShell/plugins/rtube
```

### Eltávolítás

```sh
sudo pacman -R rtube      # Arch
sudo apt remove rtube     # Ubuntu / Linux Mint
rm -rf ~/.local/share/rtube   # opcionális: a letöltött yt-dlp / deno
```

### Licenc

[MIT](LICENSE)
