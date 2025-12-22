# Portainer Install (MakeMKV Local Build)

This folder is the Portainer install path for **local builds that include MakeMKV**.

Steps:
1. Run the host setup script (downloads helpers, sets up USB automount + Samba, optional NVIDIA toolkit):
   ```
   curl -fsSL https://raw.githubusercontent.com/thashiznit2003/AutoEncoder/main/necessary-scripts/host_setup_portainer.sh -o /tmp/host_setup_portainer.sh && \
   chmod +x /tmp/host_setup_portainer.sh && \
   sudo /tmp/host_setup_portainer.sh
   ```
2. In Portainer, go to **Stacks** → **Add stack** and paste `portainer/docker-compose.yml`.
3. Deploy the stack.

Note: This compose expects the image to be built locally from source (including MakeMKV tarballs).
