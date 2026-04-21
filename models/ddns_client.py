"""
Client DDNS Infomaniak - Module principal.

Ce module fournit un client robuste et optimisé pour maintenir à jour
les enregistrements DNS Infomaniak avec l'adresse IP publique actuelle.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
import signal
import socket
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, ClassVar, Final

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# Configuration du logging
# =============================================================================

logger = logging.getLogger("ddns-infomaniak")


def clean_env(value: str) -> str:
    """Nettoie une valeur d'environnement (supprime guillemets et espaces)."""
    value = value.strip()
    # Supprime les guillemets englobants si presents
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return value.strip()


def setup_logging(level: str = "INFO") -> None:
    """Configure le logging avec un format structuré."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.setLevel(log_level)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False


# =============================================================================
# Types et constantes
# =============================================================================


class IPVersion(Enum):
    """Version du protocole IP."""

    IPV4 = 4
    IPV6 = 6

    @property
    def socket_family(self) -> socket.AddressFamily:
        """Retourne la famille de socket correspondante."""
        return socket.AF_INET if self == IPVersion.IPV4 else socket.AF_INET6

    def __str__(self) -> str:
        return f"IPv{self.value}"


class UpdateStatus(Enum):
    """Statut de la mise à jour DNS."""

    SUCCESS = "success"
    NO_CHANGE = "no_change"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class UpdateResult:
    """Résultat d'une tentative de mise à jour DNS."""

    status: UpdateStatus
    ip_version: IPVersion
    ip_address: str | None = None
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class DDNSConfig:
    """Configuration du client DDNS Infomaniak."""

    # Paramètres obligatoires
    hostname: str
    username: str
    password: str

    # Paramètres optionnels avec valeurs par défaut
    interval_seconds: int = 300
    enable_ipv6: bool = False
    log_level: str = "INFO"

    # Paramètres avancés
    request_timeout: int = 15
    max_retries: int = 3
    retry_backoff_factor: float = 1.0

    # Constantes (non modifiables)
    MIN_INTERVAL: ClassVar[int] = 15
    USER_AGENT: ClassVar[str] = (
        "Infomaniak-DDNS/2.0 (+https://github.com/axioneer-studio/ddns-infomaniak)"
    )
    INFOMANIAK_API_URL: ClassVar[str] = "https://infomaniak.com/nic/update"

    # Services de détection IP (avec failover)
    IPV4_SERVICES: ClassVar[tuple[str, ...]] = (
        "https://api.ipify.org?format=json",
        "https://api.my-ip.io/v2/ip.json",
        "https://ipv4.icanhazip.com",
    )
    IPV6_SERVICES: ClassVar[tuple[str, ...]] = (
        "https://api64.ipify.org?format=json",
        "https://api6.my-ip.io/v2/ip.json",
        "https://ipv6.icanhazip.com",
    )

    def __post_init__(self) -> None:
        """Validation et normalisation de la configuration."""
        # Validation des champs obligatoires
        if not self.hostname or not self.hostname.strip():
            raise ValueError("Le hostname est obligatoire")
        if not self.username or not self.username.strip():
            raise ValueError("Le username est obligatoire")
        if not self.password:
            raise ValueError("Le password est obligatoire")

        # Normalisation
        object.__setattr__(self, "hostname", self.hostname.strip().lower())
        object.__setattr__(self, "username", self.username.strip())

        # Sécurité: intervalle minimum
        if self.interval_seconds < self.MIN_INTERVAL:
            logger.warning(
                "Intervalle %ds trop court, ajusté à %ds (minimum)",
                self.interval_seconds,
                self.MIN_INTERVAL,
            )
            object.__setattr__(self, "interval_seconds", self.MIN_INTERVAL)

    @classmethod
    def from_env(cls) -> DDNSConfig:
        """Crée une configuration depuis les variables d'environnement."""

        configs = cls.from_env_list()
        return configs[0]

    @classmethod
    def from_env_list(cls) -> list[DDNSConfig]:
        """Crée une liste de configurations depuis les variables d'environnement."""

        hostname_key_pattern = re.compile(r"^INFOMANIAK_DDNS_HOSTNAME_(\d+)$")
        indexed_ids: set[int] = set()

        for env_key in os.environ:
            match = hostname_key_pattern.match(env_key)
            if match:
                indexed_ids.add(int(match.group(1)))

        interval = int(clean_env(os.getenv("DDNS_INTERVAL_SECONDS", "300")))
        enable_ipv6 = clean_env(os.getenv("DDNS_ENABLE_IPV6", "false")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        log_level = clean_env(os.getenv("DDNS_LOG_LEVEL", "INFO")).upper()

        # Paramètres avancés
        timeout = int(clean_env(os.getenv("DDNS_REQUEST_TIMEOUT", "15")))
        max_retries = int(clean_env(os.getenv("DDNS_MAX_RETRIES", "3")))
        backoff = float(clean_env(os.getenv("DDNS_RETRY_BACKOFF", "1.0")))

        configs: list[DDNSConfig] = []

        if indexed_ids:
            for config_id in sorted(indexed_ids):
                hostname = clean_env(
                    os.getenv(f"INFOMANIAK_DDNS_HOSTNAME_{config_id}", "")
                )
                username = clean_env(
                    os.getenv(f"INFOMANIAK_DDNS_USERNAME_{config_id}", "")
                )
                password = clean_env(
                    os.getenv(f"INFOMANIAK_DDNS_PASSWORD_{config_id}", "")
                )

                missing_fields: list[str] = []
                if not hostname:
                    missing_fields.append(f"INFOMANIAK_DDNS_HOSTNAME_{config_id}")
                if not username:
                    missing_fields.append(f"INFOMANIAK_DDNS_USERNAME_{config_id}")
                if not password:
                    missing_fields.append(f"INFOMANIAK_DDNS_PASSWORD_{config_id}")

                if missing_fields:
                    joined_missing = ", ".join(missing_fields)
                    raise ValueError(
                        f"Configuration DDNS #{config_id} incomplète: {joined_missing}"
                    )

                configs.append(
                    cls(
                        hostname=hostname,
                        username=username,
                        password=password,
                        interval_seconds=interval,
                        enable_ipv6=enable_ipv6,
                        log_level=log_level,
                        request_timeout=timeout,
                        max_retries=max_retries,
                        retry_backoff_factor=backoff,
                    )
                )

            return configs

        hostname = clean_env(os.getenv("INFOMANIAK_DDNS_HOSTNAME", ""))
        username = clean_env(os.getenv("INFOMANIAK_DDNS_USERNAME", ""))
        password = clean_env(os.getenv("INFOMANIAK_DDNS_PASSWORD", ""))

        configs.append(
            cls(
                hostname=hostname,
                username=username,
                password=password,
                interval_seconds=interval,
                enable_ipv6=enable_ipv6,
                log_level=log_level,
                request_timeout=timeout,
                max_retries=max_retries,
                retry_backoff_factor=backoff,
            )
        )

        return configs


# =============================================================================
# Métriques
# =============================================================================


@dataclass
class DDNSMetrics:
    """Métriques et statistiques du client DDNS."""

    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_checks: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    skipped_updates: int = 0
    last_ipv4: str | None = None
    last_ipv6: str | None = None
    last_update_time: datetime | None = None
    last_error: str | None = None
    consecutive_errors: int = 0

    def record_check(self) -> None:
        """Enregistre une vérification."""
        self.total_checks += 1

    def record_success(self, ip_version: IPVersion, ip: str) -> None:
        """Enregistre une mise à jour réussie."""
        self.successful_updates += 1
        self.consecutive_errors = 0
        self.last_update_time = datetime.now(timezone.utc)
        self.last_error = None

        if ip_version == IPVersion.IPV4:
            self.last_ipv4 = ip
        else:
            self.last_ipv6 = ip

    def record_failure(self, error: str) -> None:
        """Enregistre un échec."""
        self.failed_updates += 1
        self.consecutive_errors += 1
        self.last_error = error

    def record_skip(self) -> None:
        """Enregistre une mise à jour ignorée."""
        self.skipped_updates += 1

    @property
    def uptime_seconds(self) -> float:
        """Durée d'exécution en secondes."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def summary(self) -> str:
        """Retourne un résumé des métriques."""
        uptime_hours = self.uptime_seconds / 3600
        return (
            f"Uptime: {uptime_hours:.1f}h | "
            f"Checks: {self.total_checks} | "
            f"Updates: {self.successful_updates} OK, {self.failed_updates} KO, {self.skipped_updates} skip | "
            f"IPv4: {self.last_ipv4 or 'N/A'} | "
            f"IPv6: {self.last_ipv6 or 'N/A'}"
        )


# =============================================================================
# Client DDNS
# =============================================================================


class InfomaniakDDNSClient:
    """
    Client robuste pour la mise à jour DNS dynamique Infomaniak.

    Fonctionnalités:
        - Support IPv4 et IPv6
        - Retry avec backoff exponentiel
        - Failover entre plusieurs services de détection IP
        - Arrêt gracieux sur signaux système
        - Métriques et statistiques
        - Logging structuré

    Example:
        >>> config = DDNSConfig.from_env()
        >>> client = InfomaniakDDNSClient(config)
        >>> client.run_forever()
    """

    def __init__(self, config: DDNSConfig) -> None:
        """
        Initialise le client DDNS.

        Args:
            config: Configuration du client.
        """
        self.config: Final = config
        self.metrics = DDNSMetrics()
        self._running = True
        self._session: requests.Session | None = None

        # Cache des dernières IPs tentées (anti-boucle)
        self._attempted_ips: dict[IPVersion, str | None] = {
            IPVersion.IPV4: None,
            IPVersion.IPV6: None,
        }

        # Configuration du logging
        setup_logging(config.log_level)

        # Enregistrement des gestionnaires de signaux
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Configure les gestionnaires de signaux pour un arrêt gracieux."""

        def handle_shutdown(signum: int, frame: object) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Signal %s reçu, arrêt gracieux...", sig_name)
            self._running = False

        # SIGTERM (Docker stop) et SIGINT (Ctrl+C)
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

    @property
    def session(self) -> requests.Session:
        """Session HTTP avec retry automatique (lazy init)."""
        if self._session is None:
            self._session = requests.Session()

            # Configuration des retries
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=self.config.retry_backoff_factor,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"],
            )

            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)

            # Headers par défaut
            self._session.headers.update(
                {
                    "User-Agent": self.config.USER_AGENT,
                }
            )

        return self._session

    def close(self) -> None:
        """Ferme les ressources (session HTTP)."""
        if self._session:
            self._session.close()
            self._session = None

    # -------------------------------------------------------------------------
    # API publique
    # -------------------------------------------------------------------------

    def run_forever(self) -> None:
        """
        Boucle principale: vérifie et met à jour périodiquement.

        S'arrête proprement sur signal SIGTERM ou SIGINT.
        """
        logger.info("=" * 60)
        logger.info("DDNS Infomaniak - Démarrage du service")
        logger.info("=" * 60)
        logger.info("Hostname: %s", self.config.hostname)
        logger.info("IPv6: %s", "activé" if self.config.enable_ipv6 else "désactivé")
        logger.info("Intervalle: %ds", self.config.interval_seconds)
        logger.info("=" * 60)

        try:
            while self._running:
                self._run_cycle()

                # Afficher les métriques périodiquement
                if self.metrics.total_checks % 10 == 0:
                    logger.info("📊 %s", self.metrics.summary())

                # Attente interruptible
                self._interruptible_sleep(self.config.interval_seconds)

        except Exception as exc:
            logger.exception("Erreur fatale non gérée: %s", exc)
            raise

        finally:
            self.close()
            logger.info("Service arrêté. %s", self.metrics.summary())

    def check_and_update(self, ip_version: IPVersion) -> UpdateResult:
        """
        Vérifie et met à jour l'IP pour une version donnée.

        Args:
            ip_version: Version IP à traiter (IPv4 ou IPv6).

        Returns:
            Résultat de l'opération.
        """
        logger.info("--- Vérification %s ---", ip_version)

        # 1. Obtenir l'IP publique
        public_ip = self._get_public_ip(ip_version)
        if not public_ip:
            logger.warning("Impossible d'obtenir l'IP publique %s", ip_version)
            return UpdateResult(
                status=UpdateStatus.ERROR,
                ip_version=ip_version,
                message="Échec récupération IP publique",
            )

        # 2. Valider l'IP
        if not self._validate_ip(public_ip, ip_version):
            logger.warning("IP %s invalide: %s", ip_version, public_ip)
            return UpdateResult(
                status=UpdateStatus.ERROR,
                ip_version=ip_version,
                ip_address=public_ip,
                message="IP invalide",
            )

        logger.info("IP publique %s: %s", ip_version, public_ip)

        # 3. Résoudre l'IP actuelle dans le DNS
        current_dns_ip = self._resolve_hostname(ip_version)
        if current_dns_ip:
            logger.info("IP DNS actuelle: %s", current_dns_ip)
        else:
            logger.info(
                "Aucun enregistrement %s existant pour %s",
                ip_version,
                self.config.hostname,
            )

        # 4. Comparer et décider
        if current_dns_ip == public_ip:
            logger.info("IP inchangée, aucune mise à jour nécessaire")
            self._attempted_ips[ip_version] = public_ip
            return UpdateResult(
                status=UpdateStatus.NO_CHANGE,
                ip_version=ip_version,
                ip_address=public_ip,
                message="IP identique",
            )

        # 5. Anti-boucle: éviter de retenter la même IP
        if self._attempted_ips[ip_version] == public_ip:
            logger.debug("IP déjà tentée récemment, on attend le prochain cycle")
            self.metrics.record_skip()
            return UpdateResult(
                status=UpdateStatus.SKIPPED,
                ip_version=ip_version,
                ip_address=public_ip,
                message="Déjà tentée",
            )

        # 6. Mise à jour
        return self._update_dns(public_ip, ip_version)

    # -------------------------------------------------------------------------
    # Méthodes internes
    # -------------------------------------------------------------------------

    def _run_cycle(self) -> None:
        """Exécute un cycle complet de vérification."""
        self.metrics.record_check()

        try:
            # IPv4
            result_v4 = self.check_and_update(IPVersion.IPV4)
            self._process_result(result_v4)

            # IPv6 (si activé)
            if self.config.enable_ipv6:
                result_v6 = self.check_and_update(IPVersion.IPV6)
                self._process_result(result_v6)

        except Exception as exc:
            logger.error("Erreur dans le cycle: %s", exc)
            self.metrics.record_failure(str(exc))

    def _process_result(self, result: UpdateResult) -> None:
        """Traite le résultat d'une mise à jour."""
        if result.status == UpdateStatus.SUCCESS:
            self.metrics.record_success(result.ip_version, result.ip_address or "")
        elif result.status == UpdateStatus.ERROR:
            self.metrics.record_failure(result.message)

    def _interruptible_sleep(self, seconds: int) -> None:
        """Attente interruptible par le flag _running."""
        end_time = time.monotonic() + seconds
        while self._running and time.monotonic() < end_time:
            time.sleep(min(1, end_time - time.monotonic()))

    def _get_public_ip(self, ip_version: IPVersion) -> str | None:
        """
        Récupère l'IP publique avec failover entre services.

        Args:
            ip_version: Version IP recherchée.

        Returns:
            L'IP publique ou None si échec.
        """
        services = (
            self.config.IPV4_SERVICES
            if ip_version == IPVersion.IPV4
            else self.config.IPV6_SERVICES
        )

        for service_url in services:
            try:
                ip = self._fetch_ip_from_service(service_url)
                if ip and self._validate_ip(ip, ip_version):
                    return ip
            except Exception as exc:
                logger.debug("Service %s échec: %s", service_url, exc)
                continue

        return None

    def _fetch_ip_from_service(self, url: str) -> str | None:
        """Récupère l'IP depuis un service donné."""
        response = self.session.get(url, timeout=self.config.request_timeout)
        response.raise_for_status()

        # Gestion des différents formats de réponse
        content_type = response.headers.get("content-type", "")

        if "json" in content_type:
            data = response.json()
            # Formats courants: {"ip": "..."} ou {"origin": "..."}
            return data.get("ip") or data.get("origin") or data.get("address")

        # Format texte brut
        return response.text.strip()

    def _validate_ip(self, ip: str, ip_version: IPVersion) -> bool:
        """Valide le format de l'IP."""
        try:
            addr = ipaddress.ip_address(ip)
            if ip_version == IPVersion.IPV4:
                return isinstance(addr, ipaddress.IPv4Address)
            return isinstance(addr, ipaddress.IPv6Address)
        except ValueError:
            return False

    def _resolve_hostname(self, ip_version: IPVersion) -> str | None:
        """Résout le hostname vers l'IP actuelle dans le DNS."""
        try:
            info = socket.getaddrinfo(
                self.config.hostname,
                None,
                family=ip_version.socket_family,
            )
            if info:
                return info[0][4][0]
        except socket.gaierror:
            pass
        except Exception as exc:
            logger.debug("Résolution DNS échouée: %s", exc)

        return None

    def _update_dns(self, ip: str, ip_version: IPVersion) -> UpdateResult:
        """
        Met à jour l'enregistrement DNS via l'API Infomaniak.

        Args:
            ip: Nouvelle IP à configurer.
            ip_version: Version de l'IP.

        Returns:
            Résultat de la mise à jour.
        """
        url = f"{self.config.INFOMANIAK_API_URL}?hostname={self.config.hostname}&myip={ip}"

        logger.info("Mise à jour DNS: %s -> %s", self.config.hostname, ip)

        try:
            response = self.session.get(
                url,
                auth=(self.config.username, self.config.password),
                timeout=self.config.request_timeout,
            )

            text = response.text.strip().lower()
            logger.debug("Réponse API [%d]: %s", response.status_code, text)

            # Analyse de la réponse
            result = self._parse_api_response(text, ip, ip_version)

            # Mémoriser l'IP tentée
            self._attempted_ips[ip_version] = ip

            return result

        except requests.exceptions.Timeout:
            msg = "Timeout de la requête"
            logger.error(msg)
            return UpdateResult(
                status=UpdateStatus.ERROR,
                ip_version=ip_version,
                ip_address=ip,
                message=msg,
            )

        except requests.exceptions.RequestException as exc:
            msg = f"Erreur HTTP: {exc}"
            logger.error(msg)
            return UpdateResult(
                status=UpdateStatus.ERROR,
                ip_version=ip_version,
                ip_address=ip,
                message=msg,
            )

    def _parse_api_response(
        self, text: str, ip: str, ip_version: IPVersion
    ) -> UpdateResult:
        """Parse la réponse de l'API Infomaniak."""
        # Mapping des réponses Infomaniak
        responses: dict[str, tuple[UpdateStatus, str, Callable[[], None]]] = {
            "good": (
                UpdateStatus.SUCCESS,
                "DNS mis à jour avec succès",
                lambda: logger.info("✅ DNS mis à jour"),
            ),
            "nochg": (
                UpdateStatus.NO_CHANGE,
                "IP déjà configurée",
                lambda: logger.info("✅ IP déjà à jour"),
            ),
            "nohost": (
                UpdateStatus.ERROR,
                "Hostname inconnu",
                lambda: logger.error("❌ Hostname inconnu chez Infomaniak"),
            ),
            "badauth": (
                UpdateStatus.ERROR,
                "Identifiants invalides",
                lambda: logger.error("❌ Identifiants invalides"),
            ),
            "abuse": (
                UpdateStatus.ERROR,
                "Limite/abuse détecté",
                lambda: logger.error("❌ Abuse détecté"),
            ),
            "badagent": (
                UpdateStatus.ERROR,
                "User-Agent rejeté",
                lambda: logger.error("❌ User-Agent non accepté"),
            ),
            "911": (
                UpdateStatus.ERROR,
                "Erreur serveur temporaire",
                lambda: logger.warning("⚠️ Erreur serveur, réessayer plus tard"),
            ),
        }

        for keyword, (status, message, log_action) in responses.items():
            if keyword in text:
                log_action()
                return UpdateResult(
                    status=status,
                    ip_version=ip_version,
                    ip_address=ip,
                    message=message,
                )

        # Réponse non reconnue
        logger.warning("Réponse non reconnue: %s", text)
        return UpdateResult(
            status=UpdateStatus.ERROR,
            ip_version=ip_version,
            ip_address=ip,
            message=f"Réponse inconnue: {text}",
        )


class InfomaniakDDNSService:
    """Orchestrateur pour exécuter plusieurs clients DDNS en parallèle logique."""

    def __init__(self, clients: list[InfomaniakDDNSClient]) -> None:
        if not clients:
            raise ValueError("Aucune configuration DDNS valide trouvée")
        self.clients: Final = clients

    def run_forever(self) -> None:
        """Exécute tous les clients DDNS dans une boucle unique."""
        hostnames = ", ".join(client.config.hostname for client in self.clients)
        logger.info("Configurations DDNS chargées: %d", len(self.clients))
        logger.info("Hostnames: %s", hostnames)

        intervals = {client.config.interval_seconds for client in self.clients}
        interval_seconds = min(intervals)

        if len(intervals) > 1:
            logger.warning(
                "Intervalles différents détectés (%s), utilisation du minimum: %ds",
                sorted(intervals),
                interval_seconds,
            )

        try:
            while any(client._running for client in self.clients):
                for client in self.clients:
                    if not client._running:
                        continue

                    client._run_cycle()

                    if client.metrics.total_checks % 10 == 0:
                        logger.info(
                            "📊 [%s] %s",
                            client.config.hostname,
                            client.metrics.summary(),
                        )

                self._interruptible_sleep(interval_seconds)

        except Exception as exc:
            logger.exception("Erreur fatale non gérée dans le service multi-DDNS: %s", exc)
            raise

        finally:
            for client in self.clients:
                client.close()

    def _interruptible_sleep(self, seconds: int) -> None:
        """Attente interruptible tant qu'au moins un client est actif."""
        end_time = time.monotonic() + seconds
        while any(client._running for client in self.clients) and time.monotonic() < end_time:
            time.sleep(min(1, end_time - time.monotonic()))


# =============================================================================
# Factory function (compatibilité)
# =============================================================================


def from_env_clients() -> list[InfomaniakDDNSClient]:
    """Crée une liste de clients DDNS depuis les variables d'environnement."""
    return [InfomaniakDDNSClient(config) for config in DDNSConfig.from_env_list()]


def from_env() -> InfomaniakDDNSService:
    """
    Crée un service DDNS (mono ou multi-domaines) depuis les variables d'environnement.

    Returns:
        Instance configurée du service.

    Raises:
        ValueError: Si des variables obligatoires sont manquantes.
    """
    return InfomaniakDDNSService(from_env_clients())
