FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Base tools, Python, FFmpeg/HandBrakeCLI, and MakeMKV 1.18.2
RUN apt-get update && \
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
    # Install MakeMKV runtime deps from Ubuntu repos
    apt-get install -y --no-install-recommends \
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
    mkdir -p /tmp/makemkv && \
    curl -fsSL -o /tmp/makemkv/makemkv-oss_1.18.2-1_amd64.deb https://www.makemkv.com/download/makemkv-oss_1.18.2-1_amd64.deb && \
    curl -fsSL -o /tmp/makemkv/makemkv-bin_1.18.2-1_amd64.deb https://www.makemkv.com/download/makemkv-bin_1.18.2-1_amd64.deb && \
    apt-get install -y --no-install-recommends /tmp/makemkv/*.deb && \
    rm -rf /tmp/makemkv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config.json README.md scripts ./

EXPOSE 5959

CMD ["python3", "src/autoencoder.py"]
