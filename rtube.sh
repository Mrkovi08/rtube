#!/bin/sh
# Rtube launcher (Arch + Ubuntu/Mint). RTUBE_DIR overrides the install dir (testing).
exec python3 "${RTUBE_DIR:-/usr/share/rtube}/rtube.py" "$@"
