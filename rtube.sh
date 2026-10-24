#!/bin/sh
# Rtube launcher (Arch + Ubuntu/Mint). RTUBE_DIR overrides the install dir (testing).
export GTK_THEME="${GTK_THEME:-Adwaita:dark}"
case "$1" in
  --winamp) export RTUBE_SKIN=winamp; shift ;;
esac
exec python3 "${RTUBE_DIR:-/usr/share/rtube}/rtube.py" "$@"
