FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Base tools, Python, FFmpeg/HandBrakeCLI, and MakeMKV 1.18.2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      python3 \
      python3-pip \
      python3-venv \
      ffmpeg \
      handbrake-cli \
      wget \
    && wget -q https://www.makemkv.com/download/makemkv-oss_1.18.2-1_amd64.deb \
    && wget -q https://www.makemkv.com/download/makemkv-bin_1.18.2-1_amd64.deb \
    && apt-get install -y --no-install-recommends \
      ./makemkv-oss_1.18.2-1_amd64.deb \
      ./makemkv-bin_1.18.2-1_amd64.deb \
    && rm -f makemkv-oss_1.18.2-1_amd64.deb makemkv-bin_1.18.2-1_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config.json README.md scripts ./

EXPOSE 5959

CMD ["python3", "src/autoencoder.py"]
