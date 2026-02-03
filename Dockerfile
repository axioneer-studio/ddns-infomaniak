# =============================================================================
# Infomaniak DDNS Updater - Dockerfile optimisé
# =============================================================================
# - Image multi-stage pour une taille minimale
# - Utilisateur non-root pour la sécurité
# - Healthcheck intégré
# - Labels OCI standards
# =============================================================================

# Stage 1: Build des dépendances
FROM python:3.13-slim AS builder

WORKDIR /build

# Installation des dépendances dans un virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Image finale minimale
FROM python:3.13-slim AS runtime

# Labels OCI
LABEL org.opencontainers.image.title="Infomaniak DDNS Updater" \
    org.opencontainers.image.description="Service de mise à jour DNS dynamique pour Infomaniak" \
    org.opencontainers.image.authors="axioneer-studio" \
    org.opencontainers.image.source="https://github.com/axioneer-studio/ddns-infomaniak" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.version="2.0.0"

# Créer un utilisateur non-root
RUN groupadd --gid 1000 ddns && \
    useradd --uid 1000 --gid ddns --shell /bin/false ddns

WORKDIR /app

# Copier le virtualenv depuis le builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copier le code source
COPY --chown=ddns:ddns . .

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DDNS_INTERVAL_SECONDS=300 \
    DDNS_ENABLE_IPV6=false \
    DDNS_LOG_LEVEL=INFO

# Basculer vers l'utilisateur non-root
USER ddns

# Healthcheck - vérifie que le processus Python tourne
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "python main.py" > /dev/null || exit 1

# Point d'entrée
ENTRYPOINT ["python", "main.py"]
