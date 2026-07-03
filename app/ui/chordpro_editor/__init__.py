def __getattr__(name):
    if name == "ChordProEditorWindow":
        from app.ui.chordpro_editor.editor_window import ChordProEditorWindow
        return ChordProEditorWindow
    if name == "ChordProParser":
        from app.ui.chordpro_editor.parser import parse
        class _CompatParser:
            @staticmethod
            def parse(file_path):
                doc = parse(file_path)
                return {
                    "metadata": {
                        "title": doc.metadata.title,
                        "artist": doc.metadata.artist,
                        "key": doc.metadata.key,
                    },
                    "sections": doc.sections,
                }
        return _CompatParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ChordProEditorWindow", "ChordProParser"]
