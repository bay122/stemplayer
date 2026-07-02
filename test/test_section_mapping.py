import traceback

from app.audio.fast_audio import fast_audio_load
from app.services.chord_analysis import map_chords_to_sections
from app.services.whisper import transcribe_guide_audio
from test.common import find_guide_file, get_output_dir, get_song_folder, load_stems, log, write_json, write_text


SCRIPT_NAME = "section_mapping"
MIX_SR = 44100


def main():
    output_dir = get_output_dir(SCRIPT_NAME)
    song_folder = get_song_folder()
    stems = load_stems(song_folder, mix_sr=MIX_SR)
    log("SectionMapTest", f"Cancion seleccionada: {song_folder}")

    guide_file = find_guide_file(song_folder)
    sections = []
    if guide_file is not None:
        log("SectionMapTest", f"Guide encontrado: {guide_file.name}")
        guide_audio, sr = fast_audio_load(str(guide_file), target_sr=MIX_SR)
        sections = transcribe_guide_audio(guide_audio=guide_audio, mix_sr=sr)
    else:
        log("SectionMapTest", "No se encontro guide. Se usara agrupacion Global.")

    mixed_audio, included_stems, skipped_stems = build_crema_mix(stems)
    if mixed_audio is None:
        raise RuntimeError("No hubo stems aptos para analizar acordes.")

    import soundfile as sf

    mix_wav_path = output_dir / "mapping_mix.wav"
    sf.write(str(mix_wav_path), mixed_audio, MIX_SR)
    all_chords = analyze_audio_file_with_crema_worker(str(mix_wav_path))
    chords_by_section = map_chords_to_sections(sections, all_chords)

    payload = {
        "song_folder": str(song_folder),
        "guide_file": str(guide_file) if guide_file else "",
        "included_stems": included_stems,
        "skipped_stems": skipped_stems,
        "sections": sections,
        "raw_chords": all_chords,
        "chords_by_section": chords_by_section,
    }
    write_json(output_dir / "section_mapping.json", payload)

    lines = []
    for section_name, section_chords in chords_by_section.items():
        lines.append(f"[{section_name}]")
        for chord in section_chords:
            lines.append(f"  - {chord['time']:.2f}s | {chord['duration']:.2f}s | {chord['chord']}")
        lines.append("")
    write_text(output_dir / "section_mapping.txt", "\n".join(lines))

    for section_name, section_chords in chords_by_section.items():
        print(f"[{section_name}] acordes={len(section_chords)}", flush=True)

    log("SectionMapTest", f"Resultados guardados en {output_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[SectionMapTest] ERROR: {exc}", flush=True)
        traceback.print_exc()
