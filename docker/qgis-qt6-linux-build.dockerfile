FROM qgis/qgis3-qt6-build-deps-bin-only:release-3_44

# install missing runtime dependencies
RUN dnf install --nodocs --refresh -y python-jinja2

# Create non-root user
# -m -> Create the user's home directory
# -s /bin/bash -> Set as the user's
RUN useradd -ms /bin/bash quser \
    && groupadd -f wheel \
    && usermod -aG wheel quser \
    && echo '%wheel ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER quser

RUN git clone --depth 1 --filter=blob:none --single-branch -b release-3_44 https://github.com/qgis/QGIS.git ~/QGIS/

RUN mkdir -p ~/QGIS/build && cd ~/QGIS/build && cmake -G "Ninja" \
    -DBUILD_WITH_QT6=ON \
    -DWITH_QT6=ON \
    -DWITH_QTWEBKIT=OFF \
    -DWITH_PDAL=OFF \
    ../ && ninja

WORKDIR /home/quser
