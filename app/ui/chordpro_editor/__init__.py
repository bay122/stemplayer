def __getattr__(name):
    if name == "ChordProEditorWindow":
        from app.ui.chordpro_editor.editor_window import ChordProEditorWindow
        return ChordProEditorWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ChordProEditorWindow"]
