"""A simple flow layout that wraps child widgets to new rows when full.

Adapted from Qt's official C++ example (flowlayout.cpp). It sizes its
children in rows, left-to-right, breaking to a new row when the current
row's width exceeds the layout's width minus margins. This favours
vertical scrolling over horizontal scrolling.
"""
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QStyle


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin: int = 0, h_spacing: int = 4, v_spacing: int = 4):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._h_space = h_spacing
        self._v_space = v_spacing
        self._items: list[QLayoutItem] = []

    def __del__(self):
        while self._items:
            self._items.pop(0)

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def horizontalSpacing(self) -> int:
        if self._h_space >= 0:
            return self._h_space
        return self._smart_spacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self) -> int:
        if self._v_space >= 0:
            return self._v_space
        return self._smart_spacing(QStyle.PM_LayoutVerticalSpacing)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            widget = item.widget()
            space_x = self.horizontalSpacing()
            if space_x == -1 and widget is not None:
                space_x = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton,
                    Qt.Horizontal,
                )
            space_y = self.verticalSpacing()
            if space_y == -1 and widget is not None:
                space_y = widget.style().layoutSpacing(
                    QSizePolicy.PushButton, QSizePolicy.PushButton,
                    Qt.Vertical,
                )

            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + m.bottom()

    def _smart_spacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if parent is None:
            return -1
        if parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        return parent.spacing()
