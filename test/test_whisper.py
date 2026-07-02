import os
from faster_whisper import WhisperModel

def transcribir_por_frases_logicas(ruta_audio):
    if not os.path.exists(ruta_audio):
        print(f"Error: El archivo {ruta_audio} no existe.")
        return

    print("Cargando modelo Whisper ('small')...")
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)

    print(f"Procesando con agrupación semántica: {ruta_audio}")
    
    segments, info = model.transcribe(
        ruta_audio, 
        beam_size=5, 
        language="es",
        word_timestamps=True
    )

    print("\n--- Resultado de la Transcripción (Estructura Limpia) ---")
    
    palabras_bloque = []
    tiempo_inicio = None

    for segment in segments:
        for word in segment.words:
            texto = word.word.strip()
            if not texto:
                continue

            if tiempo_inicio is None:
                tiempo_inicio = word.start

            palabras_bloque.append(texto)

            # Condición de corte: si la palabra termina en punto, cerramos el bloque
            if texto.endswith("."):
                texto_completo = " ".join(palabras_bloque)
                # Corregimos errores comunes de transcripción en la marcha
                texto_completo = texto_completo.replace("Pre -corro", "Pre-coro")
                texto_completo = texto_completo.replace("Corro", "Coro")
                
                print(f"[{tiempo_inicio:.2f}s -> {word.end:.2f}s]  {texto_completo}")
                
                # Reiniciamos para la siguiente frase
                palabras_bloque = []
                tiempo_inicio = None

    # Imprimir remanentes si existen
    if palabras_bloque:
        texto_completo = " ".join(palabras_bloque)
        print(f"[{tiempo_inicio:.2f}s -> {word.end:.2f}s]  {texto_completo}")

if __name__ == "__main__":
    ruta_archivo_wav = "CUES.wav"
    transcribir_por_frases_logicas(ruta_archivo_wav)