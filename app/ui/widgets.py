"""Widgets compartidos con comportamiento personalizado."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox


class NoWheelComboBox(QComboBox):
    """QComboBox que ignora la rueda del ratón para no cambiar su valor accidentalmente.

    Por defecto, Qt hace que un QComboBox con foco cambie su valor al hacer scroll
    con la rueda. Esto es molesto cuando el combo está dentro de un panel que se
    desplaza con la rueda (porque un scroll "normal" cambia la selección sin querer).
    """

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()
