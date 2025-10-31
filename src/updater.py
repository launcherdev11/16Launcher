import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass

import requests

from version import VERSION as CURRENT_VERSION

GITHUB_API_LATEST = (
    "https://api.github.com/repos/launcherdev11/16Launcher/releases/latest"
)


@dataclass
class ReleaseInfo:
    latest_version: str
    has_update: bool
    setup_url: str | None
    sha256_url: str | None


def normalize_version(v: str) -> tuple[int, int, int]:
    parts = v.strip().lstrip("v").split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    return (major, minor, patch)


def is_newer(latest: str, current: str) -> bool:
    return normalize_version(latest) > normalize_version(current)


def get_latest_release_info() -> ReleaseInfo | None:
    try:
        resp = requests.get(GITHUB_API_LATEST, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        latest_version = (
            data.get("tag_name") or data.get("name") or ""
        ).strip()
        if not latest_version:
            logging.warning(
                "[UPDATER] Не удалось получить версию из latest release",
            )
            return None

        setup_url: str | None = None
        sha256_url: str | None = None
        for asset in data.get("assets", []) or []:
            name = asset.get("name", "")
            url = asset.get("browser_download_url")
            if not url:
                continue
            if name.lower().endswith("setup.exe"):
                setup_url = url
            elif name.upper().startswith("SHA256"):
                sha256_url = url

        has_update = is_newer(latest_version, CURRENT_VERSION)
        return ReleaseInfo(
            latest_version=latest_version.lstrip("v"),
            has_update=has_update,
            setup_url=setup_url,
            sha256_url=sha256_url,
        )
    except Exception as e:
        logging.exception(
            f"[UPDATER] Ошибка получения информации о релизе: {e}",
        )
        return None


def download_file(url: str, dest_path: str) -> bool:
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        logging.exception(f"[UPDATER] Ошибка загрузки файла: {e}")
        return False


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_expected_hash(
    sha256_text: str, target_filename: str,
) -> str | None:
    # Поддержка форматов: "<hash>  <filename>" или JSON {"filename":"hash"}
    try:
        obj = json.loads(sha256_text)
        # ожидаем словарь filename -> hash
        if isinstance(obj, dict):
            return obj.get(target_filename)
    except Exception:
        pass

    for line in sha256_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if target_filename in line:
            parts = line.split()
            if len(parts) >= 1:
                return parts[0]
    return None


def download_installer_with_verify(
    setup_url: str, sha256_url: str | None,
) -> str | None:
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix="16launcher_setup_", suffix=".exe",
        )
        os.close(fd)
        if not download_file(setup_url, temp_path):
            return None

        if sha256_url:
            resp = requests.get(sha256_url, timeout=15)
            resp.raise_for_status()
            expected = extract_expected_hash(
                resp.text, os.path.basename(setup_url),
            )
            if expected:
                actual = compute_sha256(temp_path)
                if expected.lower() != actual.lower():
                    logging.error("[UPDATER] SHA256 не совпадает, удаляю файл")
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                    return None
        return temp_path
    except Exception as e:
        logging.exception(
            f"[UPDATER] Ошибка загрузки/проверки установщика: {e}",
        )
        return None
