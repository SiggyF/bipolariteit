FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bash \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash agy
USER agy
WORKDIR /home/agy

RUN curl -fsSL https://antigravity.google/cli/install.sh | bash

ENV PATH="/home/agy/.local/bin:${PATH}"

WORKDIR /workspace

CMD ["bash"]
