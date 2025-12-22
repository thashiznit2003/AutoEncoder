# Docker Hub (Public) Image

This folder contains the Docker Hub publish artifacts. The image is **public** and labeled **beta**.

Important:
- The Docker Hub image **does not include MakeMKV** due to redistribution restrictions.
- Use the local/Portainer build path if you need MakeMKV (see the main README).

## Build & Push (Maintainer)

Example commands (run on the Docker host):

```
docker login
docker build -f dockerhub/Dockerfile -t thashiznit2003/autoencoder:beta -t thashiznit2003/autoencoder:1.25.115 .
docker push thashiznit2003/autoencoder:beta
docker push thashiznit2003/autoencoder:1.25.115
```

## One-Command Update & Publish

On the Docker host, this script pulls latest code, rebuilds + pushes the Docker Hub image, then rebuilds the local MakeMKV add-on image:

```
curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/dockerhub/update_and_publish.sh -o /tmp/update_and_publish.sh && \
chmod +x /tmp/update_and_publish.sh && \
sudo /tmp/update_and_publish.sh
```

If you want to force MakeMKV tarball re-download during the add-on build:
```
FORCE_MAKEMKV_DOWNLOAD=1 sudo /tmp/update_and_publish.sh
```

## MakeMKV Add-on (Users)

If you want MakeMKV, build a local image that layers MakeMKV on top of the Docker Hub image:

```
curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/dockerhub/with-makemkv/build_with_makemkv.sh -o /tmp/build_with_makemkv.sh && \
chmod +x /tmp/build_with_makemkv.sh && \
sudo /tmp/build_with_makemkv.sh
```

To refresh MakeMKV tarballs explicitly:
```
FORCE_MAKEMKV_DOWNLOAD=1 sudo /tmp/build_with_makemkv.sh
```

Then deploy with the Portainer compose from `portainer/docker-compose.yml` (it uses the local `linux-video-encoder:latest` image).

## Run (Users)

Use `dockerhub/docker-compose.yml`:

```
docker compose -f dockerhub/docker-compose.yml up -d
```
