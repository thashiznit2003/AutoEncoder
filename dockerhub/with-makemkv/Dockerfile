FROM thashiznit2003/autoencoder:beta

ARG MAKEMKV_VERSION=1.18.2

ENV DEBIAN_FRONTEND=noninteractive

# Build/runtime deps for MakeMKV (base image already includes ffmpeg/handbrake/etc.)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      build-essential \
      pkg-config \
      libssl-dev \
      zlib1g-dev \
      libexpat1-dev \
      qtbase5-dev \
      qtbase5-dev-tools \
      qtchooser \
      qt5-qmake \
      libavcodec-dev \
      libavformat-dev \
      libavutil-dev \
      libbluray2 \
      libcurl4 \
      libexpat1 \
      libfdk-aac2 \
      libgomp1 \
      libqt5core5a \
      libqt5gui5 \
      libqt5network5 \
      libqt5widgets5; \
    rm -rf /var/lib/apt/lists/*

# Bring in tarballs from local build context (user downloads these legally)
COPY makemkv-oss-${MAKEMKV_VERSION}.tar.gz /tmp/makemkv/makemkv-oss.tar.gz
COPY makemkv-bin-${MAKEMKV_VERSION}.tar.gz /tmp/makemkv/makemkv-bin.tar.gz

RUN set -eux; \
    mkdir -p /tmp/makemkv; \
    cd /tmp/makemkv; \
    tar --ignore-zeros -xzf makemkv-oss.tar.gz; \
    tar --ignore-zeros -xzf makemkv-bin.tar.gz; \
    cd makemkv-oss-"${MAKEMKV_VERSION}"; \
    ./configure --prefix=/usr; \
    make -s -j"$(nproc)"; \
    make -s install; \
    cd ../makemkv-bin-"${MAKEMKV_VERSION}"; \
    mkdir -p tmp; echo accepted > tmp/eula_accepted; \
    make -s -f Makefile; \
    make -s -f Makefile install; \
    ldconfig; \
    command -v makemkvcon >/dev/null 2>&1; \
    rm -rf /tmp/makemkv
