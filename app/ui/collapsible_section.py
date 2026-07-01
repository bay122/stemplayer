from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt, QSize, Signal
from app.ui.theme import current as theme


class CollapsibleSection(QWidget):
	toggled = Signal(bool)

	def __init__(self, title: str, section_id: str, config_mgr=None, parent=None):
		super().__init__(parent)
		self._section_id = section_id
		self._config_mgr = config_mgr
		self._collapsed = False
		self._content = None

		self._layout = QVBoxLayout(self)
		self._layout.setContentsMargins(0, 0, 0, 0)
		self._layout.setSpacing(0)

		self._header = QWidget()
		self._header.setCursor(Qt.PointingHandCursor)
		self._header.setStyleSheet(f"""
			QWidget {{
				background-color: {theme.BG_SECONDARY};
				border: 1px solid {theme.BG_TERTIARY};
				border-radius: {theme.BORDER_RADIUS_SM};
			}}
		""")
		self._header.setFixedHeight(26)
		hl = QHBoxLayout(self._header)
		hl.setContentsMargins(8, 0, 8, 0)
		hl.setSpacing(4)

		self._arrow = QLabel("▼")
		self._arrow.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px;")
		hl.addWidget(self._arrow)

		self._title = QLabel(title)
		self._title.setStyleSheet(f"""
			color: {theme.TEXT_PRIMARY}; font-size: 11px; font-weight: bold;
		""")
		hl.addWidget(self._title, 1)

		self._layout.addWidget(self._header)

		self._content_scroll = QScrollArea()
		self._content_scroll.setWidgetResizable(True)
		self._content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self._content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self._content_scroll.setFrameShape(QScrollArea.NoFrame)
		self._content_scroll.setStyleSheet(f"""
			QScrollArea {{
				background-color: transparent;
				border: none;
			}}
		""")
		self._content_container = QWidget()
		self._content_container.setStyleSheet(f"""
			QWidget {{
				background-color: transparent;
			}}
		""")
		self._content_layout = QVBoxLayout(self._content_container)
		self._content_layout.setContentsMargins(0, 4, 0, 0)
		self._content_layout.setSpacing(4)
		self._content_scroll.setWidget(self._content_container)
		self._layout.addWidget(self._content_scroll, 1)

		self._header.mousePressEvent = self._toggle

		if self._config_mgr:
			cs = self._config_mgr.get_collapsed_sections()
			if section_id in cs:
				self.set_collapsed(cs[section_id])
		else:
			self.set_collapsed(False)

	def set_content(self, widget):
		if self._content:
			self._content_layout.removeWidget(self._content)
			self._content.setParent(None)
		self._content = widget
		self._content_layout.addWidget(widget)

	def set_collapsed(self, collapsed: bool):
		self._collapsed = collapsed
		self._arrow.setText("▶" if collapsed else "▼")
		self._content_scroll.setVisible(not collapsed)
		if collapsed:
			self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		else:
			self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		self.updateGeometry()
		if self._config_mgr:
			self._config_mgr.set_collapsed_section(self._section_id, collapsed)
		self.toggled.emit(collapsed)

	def updateContentMinimunHeight(self, height: int):
		self._content_scroll.setMinimumHeight(height)

	def minimumSizeHint(self):
		return QSize(0, 26)

	def sizeHint(self):
		if self._collapsed:
			return QSize(100, 26)
		return super().sizeHint()

	def _toggle(self, event):
		self.set_collapsed(not self._collapsed)
