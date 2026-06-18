FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp/home \
    XDG_CACHE_HOME=/tmp/cache

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
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/home /tmp/cache \
    && fc-cache -f

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY scripts/check-pdf-toolchain.sh /usr/local/bin/check-pdf-toolchain
RUN chmod +x /usr/local/bin/check-pdf-toolchain \
    && /usr/local/bin/check-pdf-toolchain

WORKDIR /workspace

CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8000"]
