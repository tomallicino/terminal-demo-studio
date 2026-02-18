FROM ghcr.io/charmbracelet/vhs:v0.10.0

RUN if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache \
        bash \
        curl \
        ffmpeg \
        git \
        kitty \
        python3 \
        py3-pip \
        ttyd \
        xvfb \
        font-jetbrains-mono \
        nerd-fonts-jetbrains-mono; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update \
        -o Acquire::AllowReleaseInfoChange::Suite=true \
        -o Acquire::AllowReleaseInfoChange::Codename=true \
        && apt-get install -y --no-install-recommends \
        bash \
        curl \
        ffmpeg \
        git \
        kitty \
        python3 \
        python3-pip \
        xvfb \
        fonts-jetbrains-mono \
        ca-certificates && \
      rm -rf /var/lib/apt/lists/*; \
    else \
      echo "Unsupported package manager in base image" && exit 1; \
    fi

WORKDIR /app
COPY . /app/src

RUN pip3 install --break-system-packages /app/src
RUN pip3 install --break-system-packages -r /app/src/requirements.txt

RUN curl -fsSL https://starship.rs/install.sh | sh -s -- -y -v v1.24.2
RUN echo 'eval "$(starship init bash)"' >> /root/.bashrc

ENV STARSHIP_CONFIG=/app/src/assets/starship.toml

ENTRYPOINT ["/bin/bash"]
