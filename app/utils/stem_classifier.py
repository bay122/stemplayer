"""Clasificador de stems por nombre.

Detecta la categoría de un stem basándose en su nombre y en los filtros
configurados por el usuario (patrones de click, guide, etc.)."""

from typing import Optional


# Variantes conocidas de cada categoría (case-insensitive, sin acentos)
CATEGORY_VARIANTS = {
    "Vocals": [
        "vocal", "vocals", "vocale", "vocales", "voz", "voz principal",
        "voz1", "voz 1", "voz2", "voz 2", "voz3", "voz 3",
        "coro", "coros", "singer", "lead vocal", "backing",
        "cantante", "canto", "canta",
    ],
    "Drums": [
        "drum", "drums", "bateria", "batería", "percusion", "percusión",
        "kick", "snare", "hi-hat", "hihat", "tom", "cymbal", "ride",
        "platillo", "platillos", "bombo",
    ],
    "Percussion": [
        "perc", "percussion", "percusión", "percusion",
        "conga", "bongo", "bongos", "tambor", "timbales", "timbal",
        "cajon", "cajón", "pandereta", "glockenspiel", "xilofono",
        "vibraslap", "shaker", "tambourine", "cowbell", "triangulo",
    ],
    "Bass": [
        "bajo", "bass", "bajo electrico", "bajo eléctrico",
        "bajo acustico", "bajo acústico", "bajo acust", "bajo acúst",
        "contrabajo", "contrabass", "upright bass",
    ],
    "Guitars": [
        "guitarra", "guitar", "guitars", "gtr",
        "guitarra electrica", "guitarra eléctrica",
        "guitarra acustica", "guitarra acústica",
        "acoustic guitar", "electric guitar",
        "eg", "eg 1", "eg 2", "eg1", "eg2",
        "ag", "ag 1", "ag 2", "ag1", "ag2",
        "classical guitar", "cuerdas",
    ],
    "Keys": [
        "piano", "keys", "key", "keys 1", "keys 2", "keys 3",
        "key 1", "key 2", "key 3",
        "teclado", "teclados", "synth", "keyboard", "rhodes",
        "organ", "órgano", "electric piano", "ep", "piano acustico",
        "piano acústico", "piano electrico", "piano eléctrico",
        "synthesizer",
    ],
    "Ref": [
        "click", "click track", "clicktrack", "clic",
        "metro", "metronome", "metrónomo", "metronomo",
        "guide", "guia", "guía", "cue",
        "click 1", "click 2", "click 3",
        "click track 1", "click track 2",
        "reference", "referencia",
    ],
}


def _normalize(s: str) -> str:
    """Normaliza string: lowercase, sin acentos."""
    s = s.lower()
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "à": "a", "è": "e", "ì": "i", "ò": "o", "ù": "u",
        "ä": "a", "ë": "e", "ï": "i", "ö": "o", "ü": "u",
        "ñ": "n",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    return s


def get_stem_category(name: str, config_mgr=None) -> str:
    """Devuelve la categoría del stem basándose en su nombre y filtros.

    Categorías posibles: "Vocals", "Drums", "Percussion", "Bass", "Guitars",
    "Keys", "Other", "Ref" (stems de referencia como click, metro, guide, cue).
    """
    norm = _normalize(name)

    if config_mgr is not None:
        try:
            filters = config_mgr.get_stem_filters()
            ref_patterns = (
                filters.get("click_patterns", [])
                + filters.get("guide_patterns", [])
            )
            for pat in ref_patterns:
                if _normalize(pat) in norm:
                    return "Ref"
        except Exception:
            pass

    for cat, variants in CATEGORY_VARIANTS.items():
        for v in variants:
            v_norm = _normalize(v)
            if v_norm == norm:
                return cat
            if v_norm in norm or norm in v_norm:
                return cat

    return "Other"


def has_stems_of_category(state, category: str) -> bool:
    """True si el estado tiene al menos un stem de la categoría dada."""
    if not state.stems:
        return False
    for data in state.stems.values():
        cat = data.get("category", "Other")
        if cat == category:
            return True
    return False


def categories_present(state) -> list:
    """Devuelve la lista de categorías presentes en el estado."""
    cats = set()
    for data in state.stems.values():
        cats.add(data.get("category", "Other"))
    return sorted(cats)
