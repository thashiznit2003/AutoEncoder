FROM ubuntu:24.04

ARG DOCKERFILE_REV=3
ARG MAKEMKV_VERSION=1.18.2
ARG MAKEMKV_BASE_URL=https://www.makemkv.com/download
ARG MAKEMKV_BIN_URL=${MAKEMKV_BASE_URL}/makemkv-bin-${MAKEMKV_VERSION}.tar.gz
ARG MAKEMKV_OSS_URL=${MAKEMKV_BASE_URL}/makemkv-oss-${MAKEMKV_VERSION}.tar.gz

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

LABEL build.dockerfile_rev="${DOCKERFILE_REV}"

WORKDIR /linux-video-encoder

# Base tools, Python, FFmpeg/HandBrakeCLI
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends software-properties-common; \
    add-apt-repository -y universe; \
    add-apt-repository -y multiverse; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      file \
      python3 \
      python3-pip \
      python3-venv \
      ffmpeg \
      handbrake-cli; \
    rm -rf /var/lib/apt/lists/*

# Build/runtime dependencies and MakeMKV ${MAKEMKV_VERSION}
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
      libqt5widgets5 \
      sg3-utils \
      udev; \
    mkdir -p /tmp/makemkv; \
    cd /tmp/makemkv; \
    download_and_verify() { \
      url="$1"; \
      out="$2"; \
      curl -fsSL --retry 3 --retry-delay 2 "$url" -o "$out"; \
      mime="$(file -b --mime-type "$out")"; \
      case "$mime" in application/gzip|application/x-gzip) ;; \
        *) echo "Unexpected MIME type ($mime) for $out from $url" >&2; exit 1 ;; \
      esac; \
      tar -tzf "$out" >/dev/null; \
    }; \
    download_and_verify "${MAKEMKV_OSS_URL}" makemkv-oss.tar.gz; \
    download_and_verify "${MAKEMKV_BIN_URL}" makemkv-bin.tar.gz; \
    tar -xzf makemkv-oss.tar.gz; \
    tar -xzf makemkv-bin.tar.gz; \
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
    rm -rf /tmp/makemkv; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config.json README.md scripts ./

EXPOSE 5959

CMD ["python3", "src/autoencoder.py"]
