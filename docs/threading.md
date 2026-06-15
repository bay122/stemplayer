# Gestión de Hilos (Thread Safety)

## Problema resuelto: `QThread: Destroyed while thread is still running`

Este error ocurría porque las referencias a `QThread` se sobrescribían mientras el hilo subyacente seguía ejecutándose.

**Solución**: `ThreadManager` en `app/thread_manager.py` centraliza el ciclo de vida:

- `safe_replace(attr_name, new_thread)` → detiene el hilo anterior con `cancel()/stop()`, `quit()`, `wait(3000)` y `terminate()` como último recurso, **antes** de asignar el nuevo.
- `cleanup_all()` → detiene todos los hilos forzosamente (usado en `closeEvent` y `_close_song`).
- Todos los completion handlers verifican con `self.sender()` que la señal provenga del hilo **actual**, ignorando señales obsoletas de hilos reemplazados.

## Patrón correcto para crear un hilo

```python
# Antes (causaba el crash):
self.threads.loader_thread = StemLoaderThread(...)

# Después (seguro):
new_thread = StemLoaderThread(...)
self.threads.safe_replace('loader_thread', new_thread)
self.threads.safe_start(new_thread)
```
