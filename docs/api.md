# API de Terceros

## OpenRouter (Generación de Sheets ChordPro)

Para la generación de sheets ChordPro se requiere una API Key de [OpenRouter](https://openrouter.ai/). La primera vez que generes un sheet, la aplicación te pedirá la key y la almacenará en `QSettings`.

### Flujo de generación

1. La canción debe estar guardada en la librería.
2. Presiona "Generar Sheet de acordes".
3. Ingresa tu API Key de OpenRouter (se guarda en QSettings).
4. Opcionalmente pega la letra o deja que la IA la busque.
5. El sheet se genera como `.chopro` + `.sync.json` en la carpeta de la canción.
