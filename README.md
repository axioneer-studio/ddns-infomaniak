# 🌐 Infomaniak DDNS Updater

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://github.com/axioneer-studio/ddns-infomaniak/pkgs/container/ddns-infomaniak)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> Service léger et robuste pour mettre à jour automatiquement vos enregistrements DNS Infomaniak avec votre IP publique. Supporte IPv4 et IPv6.

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Démarrage rapide](#-démarrage-rapide)
- [Configuration](#️-configuration)
- [Image Docker](#-image-docker)
- [Logs et monitoring](#-logs-et-monitoring)
- [Architecture](#-architecture)
- [Sécurité](#️-sécurité)
- [Dépannage](#-dépannage)
- [Changelog](#-changelog)
- [Licence](#-licence)

---

## ✨ Fonctionnalités

| Fonctionnalité | Description |
|----------------|-------------|
| 🔄 **Mise à jour automatique** | Détecte les changements d'IP et met à jour le DNS |
| 🌍 **IPv4 & IPv6** | Support complet des deux protocoles |
| 🛡️ **Résilient** | Retry automatique avec backoff exponentiel |
| 🔀 **Failover IP** | Plusieurs services de détection IP en cas de panne |
| 📊 **Métriques** | Statistiques de fonctionnement intégrées |
| 🐳 **Docker ready** | Image optimisée, non-root, healthcheck |
| ⚡ **Arrêt gracieux** | Gestion propre des signaux SIGTERM/SIGINT |
| 📝 **Logging structuré** | Logs horodatés et niveaux configurables |

---

## 🚀 Démarrage rapide

### Prérequis Infomaniak

1. Connectez-vous au [Manager Infomaniak](https://manager.infomaniak.com)
2. Allez dans **Domaines** → votre domaine → **DNS**
3. Créez un enregistrement **DDNS** (Dynamic DNS)
4. Notez les identifiants générés : **hostname**, **username**, **password**

---

### 🐳 Option 1 : Docker Compose (recommandé)

1. Créez un fichier `.env` avec vos identifiants (voir section [Configuration](#️-configuration))

2. Créez un fichier `docker-compose.yml` :

```yaml
services:
  ddns:
    image: ghcr.io/axioneer-studio/ddns-infomaniak:latest
    container_name: ddns-infomaniak
    restart: unless-stopped
    env_file:
      - .env
    network_mode: host
```

3. Lancez le service :

```bash
docker compose up -d
```

---

### 🖥️ Option 2 : Docker CLI

```bash
docker run -d \
  --name ddns-infomaniak \
  --restart unless-stopped \
  -e INFOMANIAK_DDNS_HOSTNAME_1=ddns.example.com \
  -e INFOMANIAK_DDNS_USERNAME_1=votre-username \
  -e INFOMANIAK_DDNS_PASSWORD_1=votre-password \
  -e INFOMANIAK_DDNS_HOSTNAME_2=blog.example.com \
  -e INFOMANIAK_DDNS_USERNAME_2=votre-username-2 \
  -e INFOMANIAK_DDNS_PASSWORD_2=votre-password-2 \
  ghcr.io/axioneer-studio/ddns-infomaniak:latest
```

---

### 🐍 Option 3 : Python natif

```bash
# 1. Cloner le projet
git clone https://github.com/axioneer-studio/ddns-infomaniak.git
cd ddns-infomaniak

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Créer un fichier .env
cat > .env << EOF
INFOMANIAK_DDNS_HOSTNAME_1=ddns.example.com
INFOMANIAK_DDNS_USERNAME_1=votre-username
INFOMANIAK_DDNS_PASSWORD_1=votre-password

INFOMANIAK_DDNS_HOSTNAME_2=blog.example.com
INFOMANIAK_DDNS_USERNAME_2=votre-username-2
INFOMANIAK_DDNS_PASSWORD_2=votre-password-2
EOF

# 4. Lancer
python main.py
```

---

## ⚙️ Configuration

### Variables d'environnement

#### Obligatoires

Mode multi-domaines (recommandé) : utilisez les variables suffixées avec un index `X`.

| Variable | Description | Exemple |
|----------|-------------|---------|
| `INFOMANIAK_DDNS_HOSTNAME_X` | Hostname complet à mettre à jour | `ddns.example.com` |
| `INFOMANIAK_DDNS_USERNAME_X` | Identifiant DDNS Infomaniak | `abc123` |
| `INFOMANIAK_DDNS_PASSWORD_X` | Mot de passe DDNS | `xyz789` |

`X` peut être `1`, `2`, `3`, ... sans limite pratique.

Mode simple (legacy) également supporté pour un seul domaine :

- `INFOMANIAK_DDNS_HOSTNAME`
- `INFOMANIAK_DDNS_USERNAME`
- `INFOMANIAK_DDNS_PASSWORD`

#### Optionnelles

| Variable | Défaut | Description |
|----------|:------:|-------------|
| `DDNS_INTERVAL_SECONDS` | `300` | Intervalle entre vérifications (min: 15s) |
| `DDNS_ENABLE_IPV6` | `false` | Activer IPv6 (`true` / `false`) |
| `DDNS_LOG_LEVEL` | `INFO` | Niveau de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DDNS_REQUEST_TIMEOUT` | `15` | Timeout HTTP en secondes |
| `DDNS_MAX_RETRIES` | `3` | Nombre de tentatives en cas d'échec |
| `DDNS_RETRY_BACKOFF` | `1.0` | Facteur de backoff exponentiel |

---

### Exemple de fichier `.env`

```dotenv
# Obligatoire (multi-domaines)
INFOMANIAK_DDNS_HOSTNAME_1=ddns.example.com
INFOMANIAK_DDNS_USERNAME_1=mon-user
INFOMANIAK_DDNS_PASSWORD_1=mon-password

INFOMANIAK_DDNS_HOSTNAME_2=blog.example.com
INFOMANIAK_DDNS_USERNAME_2=mon-user-2
INFOMANIAK_DDNS_PASSWORD_2=mon-password-2

# Optionnel
DDNS_INTERVAL_SECONDS=300
DDNS_ENABLE_IPV6=false
DDNS_LOG_LEVEL=INFO
```

> ⚠️ **Ne commitez jamais** votre fichier `.env` ! Ajoutez-le au `.gitignore`.

---

## 🐳 Image Docker

### Registry

```
ghcr.io/axioneer-studio/ddns-infomaniak
```

### Tags

| Tag | Description |
|-----|-------------|
| `latest` | Dernière version stable |
| `2.x.x` | Version spécifique |
| `dev` | Branche développement |

### Caractéristiques

- 🏗️ **Multi-stage build** — Image minimale (~50 MB)
- 👤 **Non-root** — Exécution sécurisée (UID 1000)
- 🏥 **Healthcheck** — Surveillance automatique
- 🏷️ **Labels OCI** — Métadonnées standardisées

---

## 📊 Logs et monitoring

### Consulter les logs

```bash
# Temps réel
docker logs -f ddns-infomaniak

# 50 dernières lignes
docker logs --tail 50 ddns-infomaniak
```

### Exemple de sortie

```
2026-02-03 14:30:00 | INFO    | ============================================================
2026-02-03 14:30:00 | INFO    | DDNS Infomaniak - Démarrage du service
2026-02-03 14:30:00 | INFO    | ============================================================
2026-02-03 14:30:00 | INFO    | Hostname: ddns.example.com
2026-02-03 14:30:00 | INFO    | IPv6: désactivé
2026-02-03 14:30:00 | INFO    | Intervalle: 300s
2026-02-03 14:30:00 | INFO    | --- Vérification IPv4 ---
2026-02-03 14:30:01 | INFO    | IP publique IPv4: 203.0.113.42
2026-02-03 14:30:01 | INFO    | IP DNS actuelle: 203.0.113.10
2026-02-03 14:30:01 | INFO    | Mise à jour DNS: ddns.example.com -> 203.0.113.42
2026-02-03 14:30:02 | INFO    | ✅ DNS mis à jour
```

### Métriques périodiques

Toutes les 10 vérifications :

```
📊 Uptime: 2.5h | Checks: 30 | Updates: 2 OK, 0 KO, 28 skip | IPv4: 203.0.113.42 | IPv6: N/A
```

---

## 🔧 Architecture

```
ddns-infomaniak/
├── main.py                 # Point d'entrée
├── models/
│   ├── __init__.py
│   └── ddns_client.py      # Logique métier
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

### Composants

| Classe | Rôle |
|--------|------|
| `DDNSConfig` | Configuration validée |
| `DDNSMetrics` | Statistiques de fonctionnement |
| `InfomaniakDDNSClient` | Client principal |
| `IPVersion` | Enum IPv4/IPv6 |
| `UpdateResult` | Résultat des opérations |

---

## 🛡️ Sécurité

- ⚠️ **Ne versionnez jamais** vos identifiants
- 🔐 Utilisez des **variables d'environnement** ou un gestionnaire de secrets
- 🔄 Si exposés, **régénérez immédiatement** vos identifiants dans Infomaniak
- 👤 L'image Docker tourne en **utilisateur non-root**

---

## 🐛 Dépannage

| Erreur | Cause | Solution |
|--------|-------|----------|
| `badauth` | Identifiants invalides | Vérifiez username/password |
| `nohost` | Hostname inconnu | Vérifiez l'enregistrement DDNS |
| `abuse` | Trop de requêtes | Augmentez `DDNS_INTERVAL_SECONDS` |
| `911` | Erreur serveur Infomaniak | Réessai automatique |

### Mode debug

```bash
docker run -e DDNS_LOG_LEVEL=DEBUG ... ghcr.io/axioneer-studio/ddns-infomaniak:latest
```

---

## 📝 Changelog


## v2.1.0

- 🚀 **Support multi-domaines illimité** :
  - Utilisez `INFOMANIAK_DDNS_HOSTNAME_X`, `INFOMANIAK_DDNS_USERNAME_X`, `INFOMANIAK_DDNS_PASSWORD_X` (X = 1, 2, 3, ...)
  - Plus aucune limite de domaines gérés (seule la capacité machine ou l’API Infomaniak limite)
  - Mode simple (non indexé) toujours supporté pour rétrocompatibilité
- 📄 `.env.example` et documentation mis à jour avec exemples multi-domaines
- 🛠️ Orchestrateur intégré : chaque domaine est traité indépendamment à chaque cycle


### v2.0.3

- 🐳 Docker Compose simplifié avec `env_file`
- 🔧 Nettoyage automatique des guillemets dans les variables d'environnement
- 📝 Documentation mise à jour

### v2.0.0

- ✨ Refactoring complet OOP
- 🔄 Retry avec backoff exponentiel
- 🔀 Failover multi-services IP
- 📊 Métriques intégrées
- 🛑 Arrêt gracieux (SIGTERM/SIGINT)
- 📝 Logging structuré configurable
- 🐳 Dockerfile multi-stage (non-root, healthcheck)
- 📦 Support fichier `.env`

### v1.0.0

- 🎉 Version initiale

---

## 📄 Licence

[MIT](LICENSE) — Libre d'utilisation, modification et distribution.

---

## 🤝 Contribution

Les contributions sont bienvenues ! Ouvrez une **issue** ou une **pull request**.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/axioneer-studio">Axioneer Studio</a>
</p>
