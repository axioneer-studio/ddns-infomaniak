#!/usr/bin/env python3
"""
Infomaniak DDNS Updater - Point d'entrée principal.

Service léger qui maintient automatiquement à jour les enregistrements
DNS Infomaniak avec l'adresse IP publique actuelle.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

from models.ddns_client import from_env

# Charger le fichier .env s'il existe (pour exécution locale)
load_dotenv(Path(__file__).parent / ".env")


def main() -> int:
    """
    Point d'entrée principal du service DDNS.

    Returns:
        Code de sortie (0 = succès, 1 = erreur).
    """
    try:
        client = from_env()
        client.run_forever()
        return 0

    except ValueError as exc:
        print(f"❌ Erreur de configuration: {exc}", file=sys.stderr)
        print("\nVariables d'environnement requises:", file=sys.stderr)
        print("  - INFOMANIAK_DDNS_HOSTNAME", file=sys.stderr)
        print("  - INFOMANIAK_DDNS_USERNAME", file=sys.stderr)
        print("  - INFOMANIAK_DDNS_PASSWORD", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\n👋 Arrêt demandé par l'utilisateur.")
        return 0

    except Exception as exc:
        print(f"❌ Erreur fatale: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
