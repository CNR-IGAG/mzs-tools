FROM qgis/qgis3-ubuntu-qt6-build-deps-bin-only:master

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    default-jre \
    bison build-essential ca-certificates ccache cmake cmake-curses-gui dh-python expect flex flip gdal-bin git graphviz grass-dev libcups2-dev libdraco-dev libexiv2-dev libexpat1-dev libfcgi-dev libgdal-dev libgeographiclib-dev libgeos-dev libgsl-dev libmeshoptimizer-dev libpq-dev libproj-dev libprotobuf-dev libqca-qt6-dev libqca-qt6-plugins libqscintilla2-qt6-dev libsfcgal-dev libspatialite-dev libsqlite3-dev libsqlite3-mod-spatialite libyaml-tiny-perl libzip-dev libzstd-dev lighttpd locales ninja-build nlohmann-json3-dev ocl-icd-opencl-dev opencl-headers pandoc pkgconf poppler-utils protobuf-compiler pyqt6-dev pyqt6-dev-tools pyqt6.qsci-dev python3-all-dev python3-autopep8 python3-dev python3-gdal python3-matplotlib python3-mock python3-nose2 python3-owslib python3-packaging python3-psycopg2 python3-pyqt6 python3-pyqt6.qsci python3-pyqt6.qtmultimedia python3-pyqt6.qtpositioning python3-pyqt6.qtserialport python3-pyqt6.qtsvg python3-pyqt6.sip python3-pyqtbuild python3-termcolor python3-yaml qt6-3d-assimpsceneimport-plugin qt6-3d-defaultgeometryloader-plugin qt6-3d-dev qt6-3d-gltfsceneio-plugin qt6-3d-scene2d-plugin qt6-5compat-dev qt6-base-dev qt6-base-private-dev qt6-multimedia-dev qt6-positioning-dev qt6-serialport-dev qt6-svg-dev qt6-tools-dev qt6-tools-dev-tools qt6-webengine-dev qtkeychain-qt6-dev sip-tools spawn-fcgi xauth xfonts-100dpi xfonts-75dpi xfonts-base xfonts-scalable xvfb \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with sudo privileges
# -m: Create the user's home directory
# -s: Set the user's shell
RUN useradd -ms /bin/bash quser \
    && groupadd -f wheel \
    && usermod -aG wheel quser \
    && echo '%wheel ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER quser

RUN git clone --depth 1 --filter=blob:none --single-branch https://github.com/qgis/QGIS.git ~/QGIS/

RUN mkdir -p ~/QGIS/build && cd ~/QGIS/build && cmake -G "Ninja" \
    -DBUILD_WITH_QT6=ON \
    -DWITH_QT6=ON \
    -DWITH_PDAL=OFF \
    -DWITH_INTERNAL_SPATIALINDEX=TRUE \
    ../ && ninja

WORKDIR /home/quser
