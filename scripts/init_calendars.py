#!/usr/bin/env python3
"""Script pour initialiser les calendriers locaux dans Home Assistant.

Ce script crée automatiquement :
1. Un calendrier local "Télétravail"
2. Un calendrier local "Jours fériés"

Utilisation:
    python scripts/init_calendars.py <ha_url> <api_token>
    
Exemple:
    python scripts/init_calendars.py http://localhost:8123 eyJhbGc...
"""

import argparse
import json
import sys
from pathlib import Path

import requests


def create_local_calendar(ha_url: str, token: str, name: str) -> bool:
    """Crée un calendrier local via l'API Home Assistant.
    
    Args:
        ha_url: URL de Home Assistant (ex: http://localhost:8123)
        token: Token d'authentification
        name: Nom du calendrier
        
    Returns:
        True si succès, False sinon
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # Slugify le nom pour l'entity_id
    slug = name.lower().replace(" ", "_").replace("é", "e").replace("è", "e").replace("ê", "e")
    
    data = {
        "action": "create",
        "name": name,
    }
    
    url = f"{ha_url}/api/calendars"
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        response.raise_for_status()
        print(f"✓ Calendrier '{name}' créé avec succès")
        return True
    except requests.exceptions.RequestException as err:
        print(f"✗ Erreur lors de la création du calendrier '{name}': {err}")
        return False


def get_local_calendars(ha_url: str, token: str) -> list:
    """Récupère la liste des calendriers locaux existants.
    
    Args:
        ha_url: URL de Home Assistant
        token: Token d'authentification
        
    Returns:
        Liste des calendriers
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    url = f"{ha_url}/api/calendars"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json() if response.text else []
    except requests.exceptions.RequestException as err:
        print(f"Erreur lors de la récupération des calendriers: {err}")
        return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialiser les calendriers locaux dans Home Assistant"
    )
    parser.add_argument(
        "ha_url",
        help="URL de Home Assistant (ex: http://localhost:8123)",
    )
    parser.add_argument(
        "token",
        help="Token d'authentification Home Assistant",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Vérifier seulement, ne pas créer",
    )
    
    args = parser.parse_args()
    
    ha_url = args.ha_url.rstrip("/")
    token = args.token
    
    print(f"Connexion à Home Assistant: {ha_url}")
    
    # Vérifier la connexion
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{ha_url}/api/", headers=headers, timeout=5)
        response.raise_for_status()
        print("✓ Authentification réussie\n")
    except requests.exceptions.RequestException as err:
        print(f"✗ Erreur de connexion: {err}")
        sys.exit(1)
    
    # Vérifier les calendriers existants
    existing = get_local_calendars(ha_url, token)
    existing_names = [cal.get("name", "") for cal in existing]
    
    print(f"Calendriers existants: {existing_names if existing_names else 'Aucun'}\n")
    
    if args.check_only:
        return
    
    # Créer les calendriers manquants
    calendars_to_create = [
        "Télétravail",
        "Jours fériés",
    ]
    
    created_count = 0
    for calendar_name in calendars_to_create:
        if calendar_name not in existing_names:
            if create_local_calendar(ha_url, token, calendar_name):
                created_count += 1
        else:
            print(f"⊘ Calendrier '{calendar_name}' existe déjà")
    
    print(f"\n✓ Initialisation terminée ({created_count} créé(s))")


if __name__ == "__main__":
    main()
