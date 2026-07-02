import os
import json
import numpy as np
import soundfile as sf
import librosa
import scipy.signal

def build_harmonic_mix(stems: dict):
    mixed_audio = None
    included = []
    skipped = []

    for name, data in stems.items():
        cat = data.get("category", "").lower()
        fname = name.lower()
        
        should_skip = (
            "click" in cat or
            "click" in fname or
            "guide" in fname or
            "cue" in fname or
            "drum" in cat or
            "bateria" in fname or
            "drum" in fname
        )
        if should_skip:
            skipped.append(name)
            continue

        included.append(name)
        if mixed_audio is None:
            mixed_audio = data["audio"].copy()
        else:
            length = max(len(mixed_audio), len(data["audio"]))
            new_mixed = np.zeros(length, dtype=np.float32)
            new_mixed[:len(mixed_audio)] += mixed_audio
            new_mixed[:len(data["audio"])] += data["audio"]
            mixed_audio = new_mixed

    return mixed_audio, included, skipped

'''
def extract_chords(y: np.ndarray, sr: int):
    # Remuestreamos a 22050Hz para acelerar el procesamiento sin perder resolución armónica
    y_resampled = librosa.resample(y, orig_sr=sr, target_sr=22050)
    sr_proc = 22050
    hop_length = 2048

    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    templates = []
    labels = []

    for i, root in enumerate(NOTES):
        t_maj = np.zeros(12)
        t_maj[i] = t_maj[(i + 4) % 12] = t_maj[(i + 7) % 12] = 1.0
        templates.append(t_maj / np.linalg.norm(t_maj))
        labels.append(root)

        t_min = np.zeros(12)
        t_min[i] = t_min[(i + 3) % 12] = t_min[(i + 7) % 12] = 1.0
        templates.append(t_min / np.linalg.norm(t_min))
        labels.append(f"{root}m")

    templates = np.array(templates)

    # chroma_cens es ideal para acordes porque es robusto a cambios de dinámica y timbre
    chroma = librosa.feature.chroma_cens(y=y_resampled, sr=sr_proc, hop_length=hop_length)
    
    similarity = np.dot(templates, chroma)
    best_matches = np.argmax(similarity, axis=0)
    
    smoothed_matches = scipy.signal.medfilt(best_matches, kernel_size=15).astype(int)

    chords = []
    current_chord = labels[smoothed_matches[0]]
    start_frame = 0

    for i in range(1, len(smoothed_matches)):
        chord = labels[smoothed_matches[i]]
        if chord != current_chord:
            dur_frames = i - start_frame
            start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
            dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)

            if dur_time >= 0.5:
                chords.append({
                    "time": round(start_time, 2),
                    "duration": round(dur_time, 2),
                    "chord": current_chord
                })

            current_chord = chord
            start_frame = i

    dur_frames = len(smoothed_matches) - start_frame
    start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
    dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)
    if dur_time >= 0.5:
        chords.append({
            "time": round(start_time, 2),
            "duration": round(dur_time, 2),
            "chord": current_chord
        })

    return chords
'''
def extract_chords(y: np.ndarray, sr: int):
    # 1. Remuestreo y separación armónica
    sr_proc = 22050
    y_resampled = librosa.resample(y, orig_sr=sr, target_sr=sr_proc)
    
    # Separar la percusión residual que pueda quedar en la mezcla armónica
    y_harmonic, _ = librosa.effects.hpss(y_resampled)
    
    # 2. Ajuste de afinación (Tuning)
    # Detecta si la pista está ligeramente desafinada respecto a A=440Hz
    tuning = librosa.estimate_tuning(y=y_harmonic, sr=sr_proc)
    
    # 3. Extracción de Cromagrama con Transformada Q-Constante (alta precisión)
    hop_length = 2048
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr_proc, tuning=tuning, hop_length=hop_length)
    
    # 4. Construcción de Plantillas de Acordes (Tríadas y Séptimas)
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    templates = []
    labels = []

    for i, root in enumerate(NOTES):
        # Mayor (1, 3, 5)
        t_maj = np.zeros(12); t_maj[i] = t_maj[(i+4)%12] = t_maj[(i+7)%12] = 1.0
        templates.append(t_maj / np.linalg.norm(t_maj))
        labels.append(root)

        # Menor (1, b3, 5)
        t_min = np.zeros(12); t_min[i] = t_min[(i+3)%12] = t_min[(i+7)%12] = 1.0
        templates.append(t_min / np.linalg.norm(t_min))
        labels.append(f"{root}m")
        
        # Séptima Dominante (1, 3, 5, b7)
        t_dom7 = np.zeros(12); t_dom7[i] = t_dom7[(i+4)%12] = t_dom7[(i+7)%12] = t_dom7[(i+10)%12] = 1.0
        templates.append(t_dom7 / np.linalg.norm(t_dom7))
        labels.append(f"{root}7")
        
        # Menor Séptima (1, b3, 5, b7)
        t_min7 = np.zeros(12); t_min7[i] = t_min7[(i+3)%12] = t_min7[(i+7)%12] = t_min7[(i+10)%12] = 1.0
        templates.append(t_min7 / np.linalg.norm(t_min7))
        labels.append(f"{root}m7")
        
        # Mayor Séptima (1, 3, 5, 7)
        t_maj7 = np.zeros(12); t_maj7[i] = t_maj7[(i+4)%12] = t_maj7[(i+7)%12] = t_maj7[(i+11)%12] = 1.0
        templates.append(t_maj7 / np.linalg.norm(t_maj7))
        labels.append(f"{root}maj7")

    templates = np.array(templates)

    # 5. Cálculo de Similitud y Suavizado
    similarity = np.dot(templates, chroma)
    best_matches = np.argmax(similarity, axis=0)
    
    # Filtro de mediana ajustado (evita saltos erráticos de acordes)
    smoothed_matches = scipy.signal.medfilt(best_matches, kernel_size=15).astype(int)

    # 6. Agrupación temporal
    chords = []
    current_chord = labels[smoothed_matches[0]]
    start_frame = 0

    for i in range(1, len(smoothed_matches)):
        chord = labels[smoothed_matches[i]]
        if chord != current_chord:
            dur_frames = i - start_frame
            start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
            dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)

            if dur_time >= 0.5: # Ignorar acordes que duren menos de medio segundo
                chords.append({
                    "time": round(start_time, 2),
                    "duration": round(dur_time, 2),
                    "chord": current_chord
                })

            current_chord = chord
            start_frame = i

    # Procesar el último acorde de la canción
    dur_frames = len(smoothed_matches) - start_frame
    start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
    dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)
    if dur_time >= 0.5:
        chords.append({
            "time": round(start_time, 2),
            "duration": round(dur_time, 2),
            "chord": current_chord
        })

    return chords

def simular_pipeline():
    song_folder = "test_cancion"
    if not os.path.isdir(song_folder):
        print(f"Error: La carpeta '{song_folder}' no existe.")
        return

    print(f"Leyendo archivos de la carpeta: {song_folder}")
    stems = {}
    mix_sr = None

    for archivo in os.listdir(song_folder):
        if archivo.endswith(".wav"):
            nombre_stem = os.path.splitext(archivo)[0]
            ruta_completa = os.path.join(song_folder, archivo)
            
            data, sr = sf.read(ruta_completa, dtype='float32')
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
                
            if mix_sr is None:
                mix_sr = sr
                
            stems[nombre_stem] = {"audio": data, "category": ""}

    if not stems:
        print("No se encontraron archivos .wav.")
        return

    print("Mezclando stems...")
    mixed_audio, included_stems, skipped_stems = build_harmonic_mix(stems)
    print(f"INCLUIDOS: {included_stems}")
    print(f"OMITIDOS: {skipped_stems}")

    if mixed_audio is None:
        print("No hay audio para procesar.")
        return

    print("Analizando acordes con librosa...")
    chords = extract_chords(mixed_audio, mix_sr)

    print(f"Total de acordes detectados: {len(chords)}")
    if chords:
        print(json.dumps(chords[:10], indent=4, ensure_ascii=False))

if __name__ == "__main__":
    simular_pipeline()