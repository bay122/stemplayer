from pathlib import Path
import tempfile
import traceback

import soundfile as sf

from lyrics_engine import analyze_audio_file_with_crema_worker, build_crema_mix
from test.common import get_output_dir, get_song_folder, load_stems, log, write_json, write_text


SCRIPT_NAME = "crema_downmix"
MIX_SR = 44100


def main():
    output_dir = get_output_dir(SCRIPT_NAME)
    song_folder = get_song_folder()
    log("CremaTest", f"Cancion seleccionada: {song_folder}")

    stems = load_stems(song_folder, mix_sr=MIX_SR)
    log("CremaTest", f"Stems cargados: {len(stems)}")

    mixed_audio, included_stems, skipped_stems = build_crema_mix(stems)
    if mixed_audio is None:
        raise RuntimeError("No hubo stems aptos para construir el downmix.")

    mix_wav_path = output_dir / "downmix_for_crema.wav"
    sf.write(str(mix_wav_path), mixed_audio, MIX_SR)
    log("CremaTest", f"Downmix guardado en: {mix_wav_path}")
    print(f"Stems incluidos: {included_stems}", flush=True)
    print(f"Stems omitidos: {skipped_stems}", flush=True)

    payload = {
        "song_folder": str(song_folder),
        "mix_wav_path": str(mix_wav_path),
        "included_stems": included_stems,
        "skipped_stems": skipped_stems,
        "chords": [],
    }

    try:
        chords = analyze_audio_file_with_crema_worker(str(mix_wav_path))
        payload["chords"] = chords
        for index, chord in enumerate(chords[:100], start=1):
            print(
                f"{index:03d}. time={chord['time']:.2f}s dur={chord['duration']:.2f}s chord={chord['chord']}",
                flush=True,
            )
        write_json(output_dir / "crema_chords.json", payload)
        write_text(
            output_dir / "crema_chords.txt",
            "\n".join(
                [
                    f"{index:03d}. {chord['time']:.2f} | {chord['duration']:.2f} | {chord['chord']}"
                    for index, chord in enumerate(chords, start=1)
                ]
            ),
        )
        log("CremaTest", f"Resultados guardados en {output_dir}")
    except Exception as exc:
        payload["error"] = str(exc)
        write_json(output_dir / "crema_error.json", payload)
        write_text(output_dir / "crema_error.txt", traceback.format_exc())
        print(f"[CremaTest] ERROR: {exc}", flush=True)
        traceback.print_exc()


if __name__ == "__main__":
    main()
