#!/bin/sh
set -eu

VERSION="${ROXX_VERSION:-$(python -c 'import roxx; print(roxx.__version__)')}"
export ROXX_VERSION="$VERSION"
python scripts/build_binaries.py
mkdir -p dist/packages
nfpm package --config packaging/nfpm.yaml --packager deb --target "dist/packages/roxx_${VERSION}_amd64.deb"
nfpm package --config packaging/nfpm.yaml --packager rpm --target "dist/packages/roxx-${VERSION}-1.x86_64.rpm"
