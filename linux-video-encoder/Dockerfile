FROM ubuntu:20.04

ARG MAKEMKV_VERSION=1.18.2

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Pre-fetch MakeMKV tarballs into build context (script downloads them before build)
COPY makemkv-*.tar.gz /tmp/makemkv/

# Base tools, Python, FFmpeg/HandBrakeCLI, and MakeMKV ${MAKEMKV_VERSION}
RUN set -ex && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      software-properties-common \
      curl \
      python3 \
      python3-pip \
      python3-venv \
      ffmpeg \
      handbrake-cli && \
    add-apt-repository -y universe && \
    add-apt-repository -y multiverse && \
    apt-get update && \
    # Install MakeMKV build/runtime deps from Ubuntu repos
    apt-get install -y --no-install-recommends \
      build-essential \
      pkg-config \
      libssl-dev \
      zlib1g-dev \
      qtbase5-dev \
      libavcodec58 \
      libavformat58 \
      libavutil56 \
      libbluray2 \
      libcurl4 \
      libexpat1 \
      libfdk-aac1 \
      libgomp1 \
      libqt5core5a \
      libqt5gui5 \
      libqt5network5 \
      libqt5widgets5 \
      libssl1.1 \
      zlib1g && \
    cd /tmp/makemkv && \
    tar xzf makemkv-oss-${MAKEMKV_VERSION}.tar.gz && \
    tar xzf makemkv-bin-${MAKEMKV_VERSION}.tar.gz && \
    cd makemkv-oss-${MAKEMKV_VERSION} && \
    ./configure && make -s && make install && \
    cd /tmp/makemkv/makemkv-bin-${MAKEMKV_VERSION} && \
    make -f makefile.linux -s && make -f makefile.linux install && \
    rm -rf /tmp/makemkv

# Clean apt caches to keep the image smaller
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config.json README.md scripts ./

EXPOSE 5959

CMD ["python3", "src/autoencoder.py"]
