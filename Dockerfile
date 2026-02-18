FROM ghcr.io/charmbracelet/vhs:v0.10.0

RUN apk add --no-cache \
    bash \
    curl \
    ffmpeg \
    git \
    python3 \
    py3-pip \
    ttyd \
    font-jetbrains-mono \
    nerd-fonts-jetbrains-mono

WORKDIR /app
COPY . /app/src

RUN pip3 install --break-system-packages /app/src
RUN pip3 install --break-system-packages -r /app/src/requirements.txt

RUN curl -fsSL https://starship.rs/install.sh | sh -s -- -y -v v1.24.2
RUN echo 'eval "$(starship init bash)"' >> /root/.bashrc

ENV STARSHIP_CONFIG=/app/src/assets/starship.toml

ENTRYPOINT ["/bin/bash"]
