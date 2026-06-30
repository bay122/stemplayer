# API de Terceros

## Proveedores IA

La app usa un **sistema extensible de proveedores** para generación de sheets ChordPro y refinamiento de sync. El registro central (`app/services/providers/`) permite agregar nuevos proveedores sin modificar la lógica de generación.

### Proveedores disponibles

| Proveedor | Código | API Key |
|---|---|---|
| OpenRouter | `openrouter` | [openrouter.ai](https://openrouter.ai/) |
| Google AI Studio | `google` | [aistudio.google.com](https://aistudio.google.com/) |

### Flujo de generación

1. La canción debe estar guardada en la librería.
2. Presiona "Generar Sheet de acordes".
3. Si es la primera vez, se abre el diálogo de configuración IA para elegir proveedor, ingresar API key y (opcional) modelo.
4. Opcionalmente pega la letra o deja que la IA la busque.
5. El sheet se genera como `.chopro` + `.sync.json` en la carpeta de la canción.

### Configuración

- La API key y modelo elegido se guardan por proveedor en `QSettings`.
- Se puede cambiar de proveedor o key en cualquier momento desde el diálogo de configuración IA o desde Settings > IA.
- El flag `--ai-model` permite override del modelo desde línea de comandos (no implementado aún).

### OpenRouter

- URL base: `https://openrouter.ai/api/v1`
- Documentación: [OpenRouter docs](https://openrouter.ai/docs)
- Soporta fallback automático a `openrouter/auto` si el modelo primario falla.

### Google AI Studio

- Usa la API nativa `generateContent` o el endpoint compatible con OpenAI.
- Soporta web search para mejorar la calidad de las letras.
- Modelos recomendados: `gemini-2.5-flash-lite`, `gemini-2.5-pro`, `gemini-2.0-flash`.

### Sync AI Refinement

Además de la generación inicial, la IA se usa para refinar timestamps:
1. **Whisper**: El usuario selecciona un stem guía → `faster-whisper` transcribe a nivel de palabra.
2. **AI Refinement**: La IA analiza el contenido ChordPro y ajusta los timestamps por sección.
3. El resultado se guarda como `.sync.json` en la carpeta de la canción.
