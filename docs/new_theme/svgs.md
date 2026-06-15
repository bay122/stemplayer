# StemDeck — SVG Inline Assets

Todos los SVG utilizados inline en la aplicación, organizados por categoría.

---

## 1. Iconos de navegación (sidebar rail)

Usados en `index.html` dentro de los botones `.rail-btn` (viewBox `0 0 24 24`, stroke-width `1.6`).

### Menú (hamburguesa)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
</svg>
```

### Library (clipboard)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <path d="M4 4h16v16H4z M4 9h16"/>
</svg>
```

### Favorites (corazón)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
</svg>
```

### Trash (papelera)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <path d="M3 6h18 M8 6V4h8v2 M19 6l-1 14H6L5 6"/>
</svg>
```

### Settings (engranaje)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <circle cx="12" cy="12" r="3"/>
  <path d="M12 2v2 M12 20v2 M4 12H2 M22 12h-2 M5 5l1.5 1.5 M17.5 17.5 19 19 M5 19l1.5-1.5 M17.5 6.5 19 5"/>
</svg>
```

### Supporters (monitor/TV)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <rect x="2" y="7" width="20" height="13" rx="2"/>
  <path d="m17 2-5 5-5-5"/>
</svg>
```

### Help (círculo con ?)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <circle cx="12" cy="12" r="9"/>
  <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .8-1 1.7 M12 17h.01"/>
</svg>
```

---

## 2. Transporte / Reproducción

### Play (triángulo)
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <path d="M6 4l14 8L6 20z"/>
</svg>
```

### Pause (dos rectángulos)
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/>
</svg>
```

### Stop (cuadrado relleno)
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <rect x="6" y="6" width="12" height="12"/>
</svg>
```

### Loop (flechas infinito)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M17 2l4 4-4 4 M3 12V8a2 2 0 0 1 2-2h16 M7 22l-4-4 4-4 M21 12v4a2 2 0 0 1-2 2H3"/>
</svg>
```

### Playhead marker (triángulo indicador en ruler)
```html
<svg viewBox="0 0 10 10" width="10" height="10">
  <polygon points="0,0 10,0 5,8" fill="var(--accent)"/>
</svg>
```
Versión en estado `no-track` (rojo):
```html
<svg viewBox="0 0 10 10" width="10" height="10">
  <polygon points="0,0 10,0 5,8" fill="#e54e4e"/>
</svg>
```

---

## 3. Topbar — Import form

### Link/URL (eslabón de cadena)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="1.8">
  <path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1 M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>
</svg>
```

### Upload (flecha arriba)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
  <path d="M12 3v12 M7 8l5-5 5 5 M5 21h14"/>
</svg>
```

### Process / Split (rayo)
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <path d="M13 2 3 14h7l-1 8 10-12h-7z"/>
</svg>
```

### File pill (nota musical con círculos)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
</svg>
```

### Notification bell (campana)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
  <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9 M13.7 21a2 2 0 0 1-3.4 0"/>
</svg>
```

---

## 4. Close / Dismiss / Acciones

### Close (X)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M18 6 6 18M6 6l12 12"/>
</svg>
```
Variante stroke-width `2.5`:
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
  <path d="M18 6 6 18M6 6l12 12"/>
</svg>
```

### Search (lupa)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>
</svg>
```

### Download / Export (flecha abajo)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
</svg>
```

### Download individual stem (flecha + rect)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M12 3v11"></path>
  <path d="m7.5 9.5 4.5 4.5 4.5-4.5"></path>
  <rect x="5" y="17" width="14" height="4" rx="1.5"></rect>
</svg>
```

### Export spinner
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
  <circle cx="12" cy="12" r="9" stroke-opacity="0.25"/><path d="M21 12a9 9 0 0 0-9-9"/>
</svg>
```

### Add section (plus / cruz)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
  <path d="M12 5v14M5 12h14"/>
</svg>
```

### Chevron / caret (flecha abajo)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
  <polyline points="6 9 12 15 18 9"/>
</svg>
```

### Star (favorito — notificación/card)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
  <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
</svg>
```

---

## 5. Iconos de Stem (pistas de audio)

Usados en `mixer.js:289-301` en el mixer horizontal (`mx-icon`).
viewBox `0 0 24 24`, stroke-width `1.9`:

### Original (nota musical)
```html
<svg class="lane-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>
</svg>
```

### Vocals (micrófono)
```html
<svg class="lane-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><path d="M12 19v3"></path>
</svg>
```

### Drums (tambor)
```html
<svg class="lane-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <path d="M7 13.5a5 5 0 0 0 10 0"></path><path d="M7 13.5h10"></path>
  <circle cx="9" cy="10" r="2.5"></circle><circle cx="15" cy="10" r="2.5"></circle>
  <path d="M4 6.5h5"></path><path d="M15 6.5h5"></path><path d="M6.5 6.5v5"></path>
  <path d="M17.5 6.5v5"></path><path d="M10 18l-2 3"></path><path d="M14 18l2 3"></path>
  <path d="M4 18l16-8"></path>
</svg>
```

### Bass (bajo)
```html
<svg class="lane-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <path d="M16.5 3h4v5h-3"></path><path d="M17.5 5.5 9.8 13.2"></path>
  <path d="M10 13c1.6 2.2 1.1 5.1-1.2 6.5-2.1 1.3-5 .5-6-1.6-.9-1.9-.1-4.1 1.8-5 .9-.4 1.8-.4 2.8-.1.1-1.1.6-2.1 1.6-2.6 1.2-.6 2.6-.1 3.2 1.1"></path>
  <path d="M6.7 16.4h.01"></path><path d="M13.5 9.5l3 3"></path>
  <path d="M18.2 3v4.6"></path><path d="M20.5 3v4"></path>
</svg>
```

### Guitar (guitarra)
```html
<svg class="lane-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <path d="M16 4.5 20 2l2 2-2.5 4"></path><path d="M18.2 5.8 10.2 13.8"></path>
  <path d="M10.5 13.5c1.1 1.7.5 4.2-1.5 5.5-2.2 1.5-5.3.8-6.3-1.3-.8-1.7.1-3.6 1.9-4.2 1-.3 1.8-.1 2.7.5.1-1.1.6-2.1 1.6-2.6 1.4-.7 2.7.2 1.6 2.1Z"></path>
  <path d="M6.5 15.1c1.3.6 2.2 1.5 2.9 2.8"></path><circle cx="7" cy="16.4" r="1.4"></circle>
  <path d="M14 8l3 3"></path>
</svg>
```

### Piano (teclado)
```html
<svg class="lane-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <rect x="3" y="5" width="18" height="14" rx="2"></rect>
  <path d="M7 5v14"></path><path d="M12 5v14"></path><path d="M17 5v14"></path>
  <path d="M9.5 5v7"></path><path d="M14.5 5v7"></path>
</svg>
```

### Other (barras ecualizador)
```html
<svg class="lane-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <path d="M4 13v-2"></path><path d="M8 17V7"></path><path d="M12 21V3"></path>
  <path d="M16 17V7"></path><path d="M20 13v-2"></path>
</svg>
```

---

## 6. Export dropdown items

### Mix icon (barras verticales)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <line x1="4" y1="9" x2="4" y2="15"/><line x1="9" y1="5" x2="9" y2="19"/>
  <line x1="14" y1="8" x2="14" y2="16"/><line x1="19" y1="4" x2="19" y2="20"/>
</svg>
```

### All Stems icon (caja / stack)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <polygon points="12 2 22 8.5 12 15 2 8.5 12 2"/><polyline points="2 15.5 12 22 22 15.5"/>
</svg>
```

### Region icon (punteros)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
  <circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/>
  <line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/>
  <line x1="8.12" y1="8.12" x2="12" y2="12"/>
</svg>
```

### Check (para item activo)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
  <polyline points="20 6 9 17 4 12"/>
</svg>
```

---

## 7. About dialog

### App icon waveform (5 barras)
```html
<svg viewBox="0 0 28 28" fill="none">
  <rect x="2" y="10" width="3" height="8" rx="1.5" fill="currentColor" opacity=".5"/>
  <rect x="7" y="6" width="3" height="16" rx="1.5" fill="currentColor" opacity=".7"/>
  <rect x="12" y="2" width="4" height="24" rx="2" fill="currentColor"/>
  <rect x="18" y="6" width="3" height="16" rx="1.5" fill="currentColor" opacity=".7"/>
  <rect x="23" y="10" width="3" height="8" rx="1.5" fill="currentColor" opacity=".5"/>
</svg>
```

### Globe (website link)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
</svg>
```

### GitHub (Octocat)
```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
</svg>
```

### Discord
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
</svg>
```

### Reddit
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/>
</svg>
```

### Instagram
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/>
</svg>
```

### X (Twitter)
```html
<svg viewBox="0 0 24 24" fill="currentColor">
  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.747l7.73-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
</svg>
```

---

## 8. SVG Generados por JS (waveform)

### Overview waveform SVG (player.js)

Generado dinámicamente en `renderOverviewWaveformPath()`. Cada stem produce un SVG así:

```html
<svg class="stem-waveform-svg" viewBox="0 ${bars} 48" preserveAspectRatio="none">
  <rect x="${i + off}" y="${y}" width="0.6" height="${h}" rx="0.3" fill="var(--stem-color)"></rect>
  <!-- ... N rects, una por barra -->
</svg>
```

- `bars`: número de barras que caben en el ancho (≈ ancho / 5).
- Cada barra: `3px` ancho, `2px` gap.
- `preserveAspectRatio="none"` para que el SVG se estire horizontalmente.
- Opacidad `0.78` + `drop-shadow` con color del stem.

### Mini-wave (mixer, generado en mixer.js)

```html
<svg class="lane-mini-wave" viewBox="0 0 80 26" preserveAspectRatio="none">
  <rect x="0" y="..." width="1" height="..." fill="${color}" opacity="0.95"></rect>
  <!-- 40 rects, 2px espaciado -->
</svg>
```

- 40 barras, viewBox width = 80 (cada barra ocupa 2 unidades).
- `preserveAspectRatio="none"` para estirar al contenedor.

---

## 9. Assets SVG externos

| Archivo | Descripción |
|---------|-------------|
| `static/imgs/stemdeck-logo-horizontal.svg` | Logo completo usado en la web. Waveform dorado + texto "StemDeck". |
| `imgs/stemdeck-svg-assets/stemdeck-icon.svg` | App icon (512x512). Fondo oscuro, waveform dorado. |
| `imgs/stemdeck-svg-assets/stemdeck-logo-horizontal.svg` | Logo horizontal (mismo que el de static). |
| `imgs/stemdeck-svg-assets/stemdeck-logo-stacked.svg` | Logo apilado (icono + palabra). |
| `imgs/stemdeck-svg-assets/stemdeck-wordmark.svg` | Solo texto "StemDeck". |
| `imgs/stemdeck-svg-assets/stemdeck-waveform-symbol.svg` | Solo el símbolo waveform (9 barras doradas). |
| `imgs/stemdeck-svg-assets/stemdeck-tray-light.svg` | Icono para bandeja del sistema (modo claro). |
| `imgs/stemdeck-svg-assets/stemdeck-tray-monochrome.svg` | Icono para bandeja del sistema (monocromo). |
| `packaging/macos/dmg-background.svg` | Background del DMG de macOS. |

El gradiente dorado usado en assets SVG:
```xml
<linearGradient id="gold" x1="..." y1="..." x2="..." y2="..." gradientUnits="userSpaceOnUse">
  <stop stop-color="#FFE38A"/>
  <stop offset="0.48" stop-color="#F2B53D"/>
  <stop offset="1" stop-color="#C98512"/>
</linearGradient>
```
