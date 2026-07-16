"""Mod-Helfer: ID-Normalisierung, PAK-Dateinamen, Workshop-Namensabfrage.

Aus game_server_manager.py ausgelagert.
"""

import os
import re

import requests

from gsm.constants import SSL_VERIFY


def _normalize_mod_id(value):
    text = str(value or "").strip()
    return text if text.isdigit() else ""


def _sanitize_pak_filename(filename):
    name = os.path.basename(str(filename or "").strip())
    if not name:
        return ""
    if not name.lower().endswith(".pak"):
        return ""
    safe = re.sub(r"[^A-Za-z0-9._\- ]", "_", name)
    safe = safe.strip(" .")
    if not safe or not safe.lower().endswith(".pak"):
        return ""
    return safe


def fetch_workshop_mod_names(mod_ids):
    """Lädt Workshop-Namen für gegebene Mod-IDs (ohne API-Key)."""
    ids = [mid for mid in (_normalize_mod_id(x) for x in (mod_ids or [])) if mid]
    if not ids:
        return {}

    payload = {"itemcount": str(len(ids))}
    for idx, mid in enumerate(ids):
        payload[f"publishedfileids[{idx}]"] = mid

    result = {}
    try:
        r = requests.post(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            data=payload,
            timeout=12,
            verify=SSL_VERIFY,
        )
        if r.status_code != 200:
            return result
        data = r.json().get("response", {}).get("publishedfiledetails", [])
        for item in data:
            pid = _normalize_mod_id(item.get("publishedfileid", ""))
            title = str(item.get("title", "")).strip()
            if pid and title:
                result[pid] = title
    except Exception:
        return result
    return result
