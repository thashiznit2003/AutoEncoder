# Developer Update Workflow

This file is for development-only update steps. End-user install instructions live in `linux-video-encoder/README.md`.

## When the app changes
1. Update version + changelog:
   - `linux-video-encoder/src/version.py`
   - `linux-video-encoder/CHANGELOG.md`
2. Publish the Docker Hub image:
   - `dockerhub/update_and_publish.sh <VERSION>`
3. Rebuild the MakeMKV overlay (uses `/linux-video-encoder/tmp`):
   - `dockerhub/with-makemkv/build_with_makemkv.sh`
4. Redeploy the Portainer stack (Update stack → Deploy).

## Notes
- Dev uses the local `linux-video-encoder:latest` image with the MakeMKV overlay.
- Commands are expected to run on the Ubuntu Docker host with `sudo`.
