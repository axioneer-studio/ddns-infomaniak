# 🌐 Infomaniak DDNS Updater

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://github.com/axioneer-studio/ddns-infomaniak/pkgs/container/ddns-infomaniak)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Service léger et robuste qui met automatiquement à jour vos enregistrements DNS Infomaniak avec votre IP publique actuelle. Supporte IPv4 et IPv6.

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

### Option 1: Docker Compose (recommandé)

Créez un fichier ``docker-compose.yml`` :

```yaml
services:
  ddns:
    image: ghcr.io/axioneer-studio/ddns-infomaniak:latest
    container_name: ddns-infomaniak
    restart: unless-stopped
    environment:
      INFOMANIAK_DDNS_HOSTNAME: "mon-domaine.example.com"
      INFOMANIAK_DDNS_USERNAME: "mon-identifiant"
      INFOMANIAK_DDNS_PASSWORD: "mon-mot-de-passe"
      DDNS_INTERVAL_SECONDS: "300"
      DDNS_ENABLE_IPV6: "false"
```

Puis lancez :

```bash
docker compose up -d
```

### Option 2: Docker CLI

```bash
docker run -d \
  --name ddns-infomaniak \
  --restart unless-stopped \
  -e INFOMANIAK_DDNS_HOSTNAME=mon-domaine.example.com \
  -e INFOMANIAK_DDNS_USERNAME=mon-identifiant \
  -e INFOMANIAK_DDNS_PASSWORD=mon-mot-de-passe \
  -e DDNS_INTERVAL_SECONDS=300 \
  ghcr.io/axioneer-studio/ddns-infomaniak:latest
```

### Option 3: Python natif

```bash
# Installation
pip install -r requirements.txt

# Configuration (Linux/macOS)
export INFOMANIAK_DDNS_HOSTNAME="mon-domaine.example.com"
export INFOMANIAK_DDNS_USERNAME="mon-identifiant"
export INFOMANIAK_DDNS_PASSWORD="mon-mot-de-passe"

# Lancement
python main.py
```

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Obligatoire | Défaut | Description |
|----------|:-----------:|:------:|-------------|
| ``INFOMANIAK_DDNS_HOSTNAME`` | ✅ | - | Nom d'hôte complet à mettre à jour (ex: ``ddns.example.com``) |
| ``INFOMANIAK_DDNS_USERNAME`` | ✅ | - | Identifiant DDNS Infomaniak |
| ``INFOMANIAK_DDNS_PASSWORD`` | ✅ | - | Mot de passe DDNS Infomaniak |
| ``DDNS_INTERVAL_SECONDS`` | ❌ | ``300`` | Intervalle entre vérifications (min: 15s) |
| ``DDNS_ENABLE_IPV6`` | ❌ | ``false`` | Activer la mise à jour IPv6 (``true``/``false``) |
| ``DDNS_LOG_LEVEL`` | ❌ | ``INFO`` | Niveau de log (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``) |
| ``DDNS_REQUEST_TIMEOUT`` | ❌ | ``15`` | Timeout des requêtes HTTP (secondes) |
| ``DDNS_MAX_RETRIES`` | ❌ | ``3`` | Nombre de tentatives en cas d'échec |
| ``DDNS_RETRY_BACKOFF`` | ❌ | ``1.0`` | Facteur de backoff exponentiel |

### Configuration Infomaniak

1. Connectez-vous à votre [Manager Infomaniak](https://manager.infomaniak.com)
2. Accédez à **Domaines** → votre domaine → **DNS**
3. Créez un enregistrement **DDNS** (Dynamic DNS)
4. Notez le **hostname**, **username** et **password** générés

---

## 🐳 Image Docker

### Registry

L'image est publiée automatiquement sur GitHub Container Registry :

```
ghcr.io/axioneer-studio/ddns-infomaniak
```

### Tags disponibles

| Tag | Description |
|-----|-------------|
| ``latest`` | Dernière version stable |
| ``x.y.z`` | Version spécifique (ex: ``2.0.0``) |
| ``dev`` | Branche de développement |

### Caractéristiques de l'image

- 🏗️ **Multi-stage build** : Image finale minimale (~50MB)
- 👤 **Non-root** : Exécution sécurisée (UID 1000)
- 🏥 **Healthcheck** : Surveillance automatique du processus
- 🏷️ **Labels OCI** : Métadonnées standardisées

---

## 📋 Portainer / Stacks

Pour Portainer, utilisez des variables de substitution :

```yaml
services:
  ddns:
    image: ghcr.io/axioneer-studio/ddns-infomaniak:latest
    container_name: ddns-infomaniak
    restart: unless-stopped
    environment:
      INFOMANIAK_DDNS_HOSTNAME: "${DDNS_HOSTNAME}"
      INFOMANIAK_DDNS_USERNAME: "${DDNS_USERNAME}"
      INFOMANIAK_DDNS_PASSWORD: "${DDNS_PASSWORD}"
      DDNS_INTERVAL_SECONDS: "300"
      DDNS_ENABLE_IPV6: "false"
```

Définissez les variables ``DDNS_HOSTNAME``, ``DDNS_USERNAME`` et ``DDNS_PASSWORD`` dans la section **Environment** de votre Stack.

---

## 📊 Logs et monitoring

### Consulter les logs

```bash
# Logs en temps réel
docker logs -f ddns-infomaniak

# Dernières 100 lignes
docker logs --tail 100 ddns-infomaniak
```

### Format des logs

```
2026-02-03 14:30:00 | INFO    | ============================================================
2026-02-03 14:30:00 | INFO    | DDNS Infomaniak - Démarrage du service
2026-02-03 14:30:00 | INFO    | ============================================================
2026-02-03 14:30:00 | INFO    | Hostname: mon-domaine.example.com
2026-02-03 14:30:00 | INFO    | IPv6: désactivé
2026-02-03 14:30:00 | INFO    | Intervalle: 300s
2026-02-03 14:30:00 | INFO    | --- Vérification IPv4 ---
2026-02-03 14:30:01 | INFO    | IP publique IPv4: 203.0.113.42
2026-02-03 14:30:01 | INFO    | IP DNS actuelle: 203.0.113.10
2026-02-03 14:30:01 | INFO    | Mise à jour DNS: mon-domaine.example.com -> 203.0.113.42
2026-02-03 14:30:02 | INFO    | ✅ DNS mis à jour
```

### Métriques affichées

Toutes les 10 vérifications, un résumé est affiché :

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
│   └── ddns_client.py      # Client DDNS (logique métier)
├── Dockerfile              # Image Docker optimisée
├── docker-compose.yml      # Exemple de déploiement
├── requirements.txt        # Dépendances Python
├── LICENSE                 # Licence MIT
└── README.md               # Documentation
```

### Composants principaux

| Classe | Rôle |
|--------|------|
| ``DDNSConfig`` | Configuration validée avec valeurs par défaut |
| ``DDNSMetrics`` | Statistiques et compteurs de fonctionnement |
| ``InfomaniakDDNSClient`` | Client principal avec boucle de mise à jour |
| ``IPVersion`` | Enum pour IPv4/IPv6 |
| ``UpdateResult`` | Résultat structuré des opérations |

---

## 🛡️ Sécurité

- ⚠️ **Ne versionnez jamais** vos identifiants dans le code source
- 🔐 Utilisez des **variables d'environnement** ou un gestionnaire de secrets
- 🔄 Si des identifiants ont été exposés, **régénérez-les** immédiatement depuis le Manager Infomaniak
- 👤 L'image Docker s'exécute en **utilisateur non-root** (UID 1000)

---

## 🐛 Dépannage

### Erreurs courantes

| Erreur | Cause | Solution |
|--------|-------|----------|
| ``badauth`` | Identifiants invalides | Vérifiez username/password dans Infomaniak |
| ``nohost`` | Hostname inconnu | Vérifiez que l'enregistrement DDNS existe |
| ``abuse`` | Trop de requêtes | Augmentez ``DDNS_INTERVAL_SECONDS`` |
| ``911`` | Erreur serveur Infomaniak | Réessayez plus tard (automatique) |

### Debug avancé

```bash
# Activer les logs DEBUG
docker run -e DDNS_LOG_LEVEL=DEBUG ... ghcr.io/axioneer-studio/ddns-infomaniak:latest
```

---

## 📝 Changelog

### v2.0.0

- ✨ Refactoring complet avec architecture orientée objet
- 🔄 Retry automatique avec backoff exponentiel
- 🔀 Failover entre plusieurs services de détection IP
- 📊 Métriques et statistiques intégrées
- 🛑 Arrêt gracieux sur SIGTERM/SIGINT
- 📝 Logging structuré avec niveaux configurables
- 🐳 Dockerfile multi-stage optimisé (non-root, healthcheck)
- ⚙️ Nouvelles options de configuration avancées

### v1.0.0

- 🎉 Version initiale

---

## 📄 Licence

MIT — voir [LICENSE](LICENSE)

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.
