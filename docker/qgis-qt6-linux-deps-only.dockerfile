FROM qgis/qgis3-qt6-build-deps-bin-only:release-3_44

# install missing runtime dependencies
RUN dnf install --nodocs --refresh -y python-jinja2 java-21-openjdk

# Create non-root user
# -m -> Create the user's home directory
# -s /bin/bash -> Set as the user's
RUN useradd -ms /bin/bash quser \
    && groupadd -f wheel \
    && usermod -aG wheel quser \
    && echo '%wheel ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER quser
WORKDIR /home/quser
