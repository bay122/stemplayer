import json
import os
from pathlib import Path
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TEST_DIR = ROOT_DIR / "test"
OUTPUT_DIR = TEST_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".flac")
GUIDE_TOKENS = ("guide", "guia", "cue", "vocal")


def log(scope: str, message: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}][{scope}] {message}", flush=True)


def read_project_config():
    config_path = ROOT_DIR / "config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def get_song_folder():
    env_song_dir = os.environ.get("STEMS_TEST_SONG_DIR", "").strip()
    if env_song_dir:
        song_dir = Path(env_song_dir)
        if song_dir.exists():
            return song_dir
        raise FileNotFoundError(f"No existe STEMS_TEST_SONG_DIR: {song_dir}")

    config = read_project_config()
    library_path = config.get("library_path", "").strip()
    env_song_name = os.environ.get("STEMS_TEST_SONG_NAME", "").strip()
    setlists = config.get("setlists", [])
    fallback_song_name = ""
    if setlists and setlists[0].get("song_ids"):
        fallback_song_name = setlists[0]["song_ids"][0]

    song_name = env_song_name or fallback_song_name
    if library_path and song_name:
        song_dir = Path(library_path) / song_name
        if song_dir.exists():
            return song_dir

    raise RuntimeError(
        "No se pudo resolver una cancion de prueba. "
        "Define STEMS_TEST_SONG_DIR o STEMS_TEST_SONG_NAME."
    )


def list_audio_files(song_folder: Path):
    return sorted(
        [path for path in song_folder.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS]
    )


def find_guide_file(song_folder: Path):
    for audio_file in list_audio_files(song_folder):
        lower_name = audio_file.stem.lower()
        if any(token in lower_name for token in GUIDE_TOKENS):
            return audio_file
    return None


def load_stems(song_folder: Path, mix_sr: int = 44100):
    from app.audio.fast_audio import fast_audio_load

    stems = {}
    for audio_file in list_audio_files(song_folder):
        audio, sr = fast_audio_load(str(audio_file), target_sr=mix_sr)
        lower_name = audio_file.stem.lower()
        category = "Other"
        if any(token in lower_name for token in ("drum", "bateria", "batería")):
            category = "Drums"
        elif any(token in lower_name for token in ("click", "metro")):
            category = "Click"
        stems[audio_file.stem] = {
            "audio": audio,
            "sr": sr,
            "category": category,
        }
    return stems


def get_output_dir(script_name: str):
    output_dir = OUTPUT_DIR / script_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
