FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.4.0 /uv /bin/uv

ENV PYTHONUNBUFFERED=1
ENV UV_HTTP_TIMEOUT=120

# Install libreoffice
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice

# Copy the Dhivehi font files into the container
COPY docker_fonts/*.ttf /usr/share/fonts/truetype/

# Update font cache
RUN fc-cache -f -v
