import os
import sys
import tempfile
from PySide6.QtCore import QThread, Signal

import requests

from app.version import APP_VERSION

REPO = "bay122/stemplayer"
GITHUB_API = f"https://api.github.com/repos/{REPO}/releases/latest"
_TIMEOUT = 10


def _parse_tag(tag: str) -> str:
    return tag.lstrip("v")


def is_newer(v1: str, v2: str) -> bool:
    a = [int(x) for x in v1.split(".")]
    b = [int(x) for x in v2.split(".")]
    for i in range(max(len(a), len(b))):
        va = a[i] if i < len(a) else 0
        vb = b[i] if i < len(b) else 0
        if va > vb:
            return True
        if va < vb:
            return False
    return False


def _platform_asset_suffix() -> str:
    if sys.platform == "win32":
        return ".exe"
    return ".deb"


def _download_path() -> str:
    suffix = _platform_asset_suffix()
    return os.path.join(tempfile.gettempdir(), f"stemplayer_update{suffix}")


class UpdateCheckThread(QThread):
    finished = Signal(object)
    error = Signal(str)

    def run(self):
        try:
            resp = requests.get(GITHUB_API, timeout=_TIMEOUT)
            if resp.status_code != 200:
                self.finished.emit(None)
                return
            data = resp.json()
            tag = _parse_tag(data.get("tag_name", ""))
            if not tag:
                self.finished.emit(None)
                return

            suffix = _platform_asset_suffix()
            download_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(suffix):
                    download_url = asset["browser_download_url"]
                    break

            self.finished.emit({
                "version": tag,
                "is_newer": is_newer(tag, APP_VERSION),
                "download_url": download_url,
                "release_notes": data.get("body", ""),
                "release_url": data.get("html_url", ""),
            })
        except requests.RequestException as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))


class UpdateDownloadThread(QThread):
    progress = Signal(int, int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._dest = _download_path()

    def dest_path(self) -> str:
        return self._dest

    def run(self):
        try:
            resp = requests.get(self._url, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(self._dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(downloaded, total)
            self.finished.emit(self._dest)
        except Exception as e:
            self.error.emit(str(e))
