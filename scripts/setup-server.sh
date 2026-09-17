#!/bin/bash
set -e
echo "=== ARIA Server Setup ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed. Log out and back in for group changes."
fi

# Install Docker Compose plugin
sudo apt install -y docker-compose-plugin

# Install Ollama
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Install Tailscale
if ! command -v tailscale &> /dev/null; then
    echo "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "Run 'sudo tailscale up' to connect to your Tailscale network"
fi

# Install NVIDIA Container Toolkit (for GPU in Docker if needed)
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected. Installing container toolkit..."
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    sudo apt update && sudo apt install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
fi

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. cp .env.example .env && edit .env"
echo "  2. ./scripts/pull-models.sh"
echo "  3. docker compose up -d"
echo "  4. docker compose exec aria-backend alembic upgrade head"
