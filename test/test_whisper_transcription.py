from pathlib import Path
import traceback

from app.audio.fast_audio import fast_audio_load
from app.services.whisper import transcribe_guide_audio
from test.common import find_guide_file, get_output_dir, get_song_folder, log, write_json, write_text


SCRIPT_NAME = "whisper_transcription"
MIX_SR = 44100
MODEL_SIZE = "base"
LANGUAGE = "es"


def main():
    output_dir = get_output_dir(SCRIPT_NAME)
    song_folder = get_song_folder()
    log("WhisperTest", f"Cancion seleccionada: {song_folder}")

    guide_file = find_guide_file(song_folder)
    if guide_file is None:
        raise RuntimeError("No se encontro una pista Guide/Guia/Cue/Vocal en la cancion elegida.")

    log("WhisperTest", f"Pista guide encontrada: {guide_file.name}")
    guide_audio, sr = fast_audio_load(str(guide_file), target_sr=MIX_SR)
    log("WhisperTest", f"Audio cargado: samples={len(guide_audio)} sr={sr}")

    sections = transcribe_guide_audio(
        guide_audio=guide_audio,
        mix_sr=sr,
        language=LANGUAGE,
        model_size=MODEL_SIZE,
    )

    for index, section in enumerate(sections, start=1):
        print(
            f"{index:02d}. start={section['start']:.2f}s end={section['end']:.2f}s label={section['label']}",
            flush=True,
        )

    write_json(output_dir / "sections.json", sections)
    write_text(
        output_dir / "sections.txt",
        "\n".join(
            [
                f"{index:02d}. {section['start']:.2f} -> {section['end']:.2f} | {section['label']}"
                for index, section in enumerate(sections, start=1)
            ]
        ),
    )
    log("WhisperTest", f"Resultados guardados en {output_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[WhisperTest] ERROR: {exc}", flush=True)
        traceback.print_exc()
