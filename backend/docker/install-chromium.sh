#!/bin/sh
# Install Chromium and the system libraries it needs.
#
# The libraries are listed by hand. `playwright install --with-deps` asks for font packages
# that do not exist on this Debian release, and then the whole install fails.
set -eu

# Fetch packages over HTTPS. Some networks block plain HTTP to the Debian mirror.
sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources

apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    fonts-unifont \
    libasound2t64 \
    libatk-bridge2.0-0t64 \
    libatk1.0-0t64 \
    libatspi2.0-0t64 \
    libcairo2 \
    libcups2t64 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2
rm -rf /var/lib/apt/lists/*

playwright install chromium
chmod -R a+rX "$PLAYWRIGHT_BROWSERS_PATH"
