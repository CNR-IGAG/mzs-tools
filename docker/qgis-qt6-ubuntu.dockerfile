FROM qgis/qgis3-ubuntu-qt6-build-deps-bin-only:master

# Install wget for downloading GPG key
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Add QGIS ubuntu-nightly Qt6 repository
RUN wget -qO /etc/apt/keyrings/qgis-archive-keyring.gpg \
    https://download.qgis.org/downloads/qgis-archive-keyring.gpg \
    && echo "Types: deb deb-src\n\
URIs: https://qgis.org/ubuntu-nightly\n\
Suites: questing\n\
Architectures: amd64\n\
Components: main\n\
Signed-By: /etc/apt/keyrings/qgis-archive-keyring.gpg" \
    > /etc/apt/sources.list.d/qgis.sources

# Install QGIS Qt6 and plugin dependencies
RUN apt-get update && apt-get install -y \
    qgis-qt6 \
    default-jre \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with sudo privileges
# -m: Create the user's home directory
# -s: Set the user's shell
RUN useradd -ms /bin/bash quser \
    && groupadd -f wheel \
    && usermod -aG wheel quser \
    && echo '%wheel ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER quser
WORKDIR /home/quser
