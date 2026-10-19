#!/bin/sh
export GTK_THEME="${GTK_THEME:-Adwaita:dark}"
case "$1" in
  --winamp) export RTUBE_SKIN=winamp; shift ;;
esac
exec python3 /usr/share/rtube/rtube.py "$@"
