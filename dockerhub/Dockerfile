FROM ubuntu:24.04

ARG DOCKERFILE_REV=1

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

LABEL build.dockerfile_rev="${DOCKERFILE_REV}" \
      build.distribution="dockerhub" \
      build.makemkv="excluded"

WORKDIR /linux-video-encoder

# Base tools, Python, FFmpeg/HandBrakeCLI (no MakeMKV in Docker Hub image)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends software-properties-common; \
    add-apt-repository -y universe; \
    add-apt-repository -y multiverse; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      file \
      python3 \
      python3-pip \
      python3-venv \
      ffmpeg \
      handbrake-cli \
      cifs-utils \
      exfat-fuse \
      exfatprogs \
      sg3-utils \
      udev \
      eject; \
    rm -rf /var/lib/apt/lists/*

COPY txt/requirements.txt ./requirements.txt
RUN python3 -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH="/venv/bin:${PATH}"

COPY linux-video-encoder/src ./src
COPY linux-video-encoder/assets ./assets
COPY linux-video-encoder/config.json linux-video-encoder/README.md ./
COPY necessary-scripts ./scripts

EXPOSE 5959

CMD ["python3", "src/autoencoder.py"]
