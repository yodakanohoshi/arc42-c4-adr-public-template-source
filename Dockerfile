FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp/home \
    XDG_CACHE_HOME=/tmp/cache \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    GRAPHVIZ_DOT=/usr/bin/dot \
    PLANTUML_JAR=/opt/plantuml/plantuml.jar

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       pandoc \
       graphviz \
       fonts-noto-cjk \
       fonts-noto-cjk-extra \
       fontconfig \
       libcairo2 \
       libpango-1.0-0 \
       libpangoft2-1.0-0 \
       libharfbuzz0b \
       libharfbuzz-subset0 \
       libgdk-pixbuf-2.0-0 \
       libffi8 \
       shared-mime-info \
       poppler-utils \
       ca-certificates \
       curl \
       default-jre-headless \
       nodejs \
       npm \
       chromium \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/home /tmp/cache \
    && fc-cache -f

# Mermaid CLI (mmdc) renders ```mermaid blocks (including C4) to images for the
# PDF. It drives the system Chromium installed above; no bundled download.
RUN npm install -g @mermaid-js/mermaid-cli@10.9.1 \
    && npm cache clean --force

# PlantUML renders ```plantuml blocks (including C4 via the bundled <C4/...>
# standard library) for both the site and the PDF. The jar is self-contained and
# drives the Graphviz `dot` installed above; the wrapper exposes it as `plantuml`.
ARG PLANTUML_VERSION=1.2024.8
RUN mkdir -p /opt/plantuml \
    && curl -fsSL -o /opt/plantuml/plantuml.jar \
       "https://github.com/plantuml/plantuml/releases/download/v${PLANTUML_VERSION}/plantuml-${PLANTUML_VERSION}.jar" \
    && printf '#!/usr/bin/env sh\nexec java -Djava.awt.headless=true -jar "%s" "$@"\n' "${PLANTUML_JAR}" > /usr/local/bin/plantuml \
    && chmod +x /usr/local/bin/plantuml \
    && plantuml -version

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY scripts/check-pdf-toolchain.sh /usr/local/bin/check-pdf-toolchain
RUN chmod +x /usr/local/bin/check-pdf-toolchain \
    && /usr/local/bin/check-pdf-toolchain

WORKDIR /workspace

CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8000"]
