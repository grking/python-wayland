FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    curl \
    bash \
    git \
    vim \
    python3 \
    python3-pip \
    xwayland-run \
    weston \
    pipx \
    && rm -rf /var/lib/apt/lists/*

RUN pipx install hatch

WORKDIR /app

CMD ["/bin/bash"]