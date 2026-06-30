import os
import json
import numpy as np
from PySide6.QtWidgets import (
	QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
	QTableWidget, QTableWidgetItem, QSlider, QLineEdit,
	QHeaderView, QMessageBox, QAbstractItemView, QStyleOptionSlider, QStyle
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QDoubleValidator
from app.ui.theme import current as theme


class SpinBoxWidget(QWidget):
	valueChanged = Signal(float)

	def __init__(self, parent=None):
		super().__init__(parent)
		self._value = 0.0
		self._min = 0.0
		self._max = 999999.0
		self._step = 0.5
		self._decimals = 2
		self._signals_blocked = False
		self._setup_ui()

	def _setup_ui(self):
		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(2)

		btn_size = 22

		self.dec_btn = QPushButton("−")
		self.dec_btn.setFixedSize(btn_size, btn_size)
		self.dec_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.BG_TERTIARY};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BORDER};
				border-radius: 3px;
				font-weight: bold;
				font-size: 12px;
				padding: 0px;
			}}
			QPushButton:hover {{
				background-color: {theme.HOVER_BRIGHTEN};
				border: 1px solid {theme.BORDER_LIGHT};
			}}
			QPushButton:pressed {{
				background-color: {theme.PRESSED_DARKEN};
			}}
		""")
		self.dec_btn.clicked.connect(self._decrement)
		layout.addWidget(self.dec_btn)

		self.line_edit = QLineEdit()
		self.line_edit.setFixedWidth(72)
		self.line_edit.setAlignment(Qt.AlignCenter)
		self.line_edit.setStyleSheet(f"""
			QLineEdit {{
				background-color: {theme.BG_PRIMARY};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BG_TERTIARY};
				border-radius: 3px;
				padding: 2px 4px;
				font-size: 12px;
			}}
			QLineEdit:focus {{
				border: 1px solid {theme.ACCENT_PRIMARY};
			}}
		""")
		validator = QDoubleValidator(self._min, self._max, self._decimals)
		validator.setNotation(QDoubleValidator.Notation.StandardNotation)
		self.line_edit.setValidator(validator)
		self.line_edit.editingFinished.connect(self._on_editing_finished)
		self.line_edit.returnPressed.connect(self._on_editing_finished)
		layout.addWidget(self.line_edit)

		self.inc_btn = QPushButton("+")
		self.inc_btn.setFixedSize(btn_size, btn_size)
		self.inc_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.BG_TERTIARY};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BORDER};
				border-radius: 3px;
				font-weight: bold;
				font-size: 12px;
				padding: 0px;
			}}
			QPushButton:hover {{
				background-color: {theme.HOVER_BRIGHTEN};
				border: 1px solid {theme.BORDER_LIGHT};
			}}
			QPushButton:pressed {{
				background-color: {theme.PRESSED_DARKEN};
			}}
		""")
		self.inc_btn.clicked.connect(self._increment)
		layout.addWidget(self.inc_btn)

		self._update_display()

	def setRange(self, min_val, max_val):
		self._min = float(min_val)
		self._max = float(max_val)
		validator = QDoubleValidator(self._min, self._max, self._decimals)
		validator.setNotation(QDoubleValidator.Notation.StandardNotation)
		self.line_edit.setValidator(validator)
		self._clamp()

	def setDecimals(self, decimals):
		self._decimals = decimals
		format_str = f"{{:.{decimals}f}}"
		self._format_str = format_str
		self._update_display()

	def setSingleStep(self, step):
		self._step = float(step)

	def setValue(self, value):
		value = float(value)
		self._value = round(value, self._decimals)
		self._clamp()
		self._update_display()

	def value(self):
		return self._value

	def blockSignals(self, block):
		self._signals_blocked = block

	def set_decrement_enabled(self, enabled):
		self.dec_btn.setEnabled(enabled)

	def set_increment_enabled(self, enabled):
		self.inc_btn.setEnabled(enabled)

	def _clamp(self):
		if self._value < self._min:
			self._value = self._min
		if self._value > self._max:
			self._value = self._max

	def _update_display(self):
		fmt = getattr(self, '_format_str', f"{{:.{self._decimals}f}}")
		self.line_edit.setText(fmt.format(self._value))

	def _emit_changed(self):
		if not self._signals_blocked:
			self.valueChanged.emit(self._value)

	def _decrement(self):
		new_val = round(self._value - self._step, self._decimals)
		if new_val >= self._min:
			self._value = new_val
			self._update_display()
			self._emit_changed()

	def _increment(self):
		new_val = round(self._value + self._step, self._decimals)
		if new_val <= self._max:
			self._value = new_val
			self._update_display()
			self._emit_changed()

	def _on_editing_finished(self):
		text = self.line_edit.text().strip()
		if not text:
			self._update_display()
			return
		try:
			val = round(float(text.replace(',', '.')), self._decimals)
			if val < self._min:
				val = self._min
			elif val > self._max:
				val = self._max
			if abs(val - self._value) > 0.001:
				self._value = val
				self._update_display()
				self._emit_changed()
			else:
				self._update_display()
		except ValueError:
			self._update_display()


class WaveformSlider(QSlider):
	def __init__(self, parent=None):
		super().__init__(Qt.Horizontal, parent)
		self._marks = []
		self._waveform = None

	def set_marks(self, positions_0_1000):
		self._marks = sorted(positions_0_1000)

	def set_waveform(self, waveform):
		self._waveform = waveform
		self.update()

	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)

		opt = QStyleOptionSlider()
		self.initStyleOption(opt)

		groove_rect = self.style().subControlRect(
			QStyle.ComplexControl.CC_Slider, opt,
			QStyle.SubControl.SC_SliderGroove, self
		)

		handle_rect = self.style().subControlRect(
			QStyle.ComplexControl.CC_Slider, opt,
			QStyle.SubControl.SC_SliderHandle, self
		)

		groove_left = groove_rect.left() + handle_rect.width() // 2
		groove_right = groove_rect.right() - handle_rect.width() // 2
		groove_width = groove_right - groove_left
		groove_height = groove_rect.height()

		if groove_width <= 0:
			super().paintEvent(event)
			painter.end()
			return

		groove_bg = QRect(groove_left, groove_rect.top(), groove_width, groove_height)

		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QBrush(QColor(theme.BG_TERTIARY)))
		painter.drawRoundedRect(groove_bg, 3, 3)

		if self._waveform is not None and len(self._waveform) > 1:
			fg = QColor(theme.ACCENT_INFO)
			fg.setAlpha(80)
			painter.setBrush(QBrush(fg))
			num_points = len(self._waveform)
			mid_y = groove_bg.center().y()
			half_h = max(2, groove_height * 2)

			for i in range(num_points):
				x = groove_left + int((i / (num_points - 1)) * groove_width)
				amplitude = self._waveform[i]
				bar_h = max(1, int(amplitude * half_h))
				painter.drawRect(x, mid_y - bar_h // 2, max(1, groove_width // num_points), bar_h)

		value_range = max(1, self.maximum() - self.minimum())
		sub_width = int((self.value() / value_range) * groove_width)
		if sub_width > 0:
			sub_rect = QRect(groove_left, groove_rect.top(), sub_width, groove_height)
			painter.setBrush(QBrush(QColor(theme.ACCENT_INFO)))
			painter.drawRoundedRect(sub_rect, 3, 3)

		handle_x = groove_left + sub_width - handle_rect.width() // 2
		handle_y = groove_rect.center().y() - handle_rect.height() // 2
		handle_r = QRect(handle_x, handle_y, handle_rect.width(), handle_rect.height())
		painter.setBrush(QBrush(QColor(theme.ACCENT_INFO)))
		painter.setPen(QPen(QColor(theme.TEXT_PRIMARY), 1))
		painter.drawEllipse(handle_r)

		if self._marks:
			painter.setPen(QPen(QColor(theme.ACCENT_WARNING), 2))
			for pos in self._marks:
				x = groove_left + int(pos / 1000.0 * groove_width)
				if 0 <= pos <= 1000:
					painter.drawLine(x, groove_rect.top() - 4, x, groove_rect.bottom() + 4)

		painter.end()


class SyncEditor(QWidget):
	saved = Signal()

	def __init__(self, controller, sync_path, chopro_path):
		super().__init__()
		self.controller = controller
		self.sync_path = sync_path
		self.chopro_path = chopro_path
		self._ignore_progress = False

		song_name = controller.state.current_song_name or "Sin cancion"
		self.setWindowTitle(f"Editor de Sincronizacion - {song_name}")
		self.resize(750, 600)

		self._setup_ui()
		self._compute_waveform()
		self._load_sync()

	def _compute_waveform(self):
		stems = self.controller.state.stems
		if not stems:
			return
		max_len = max(len(s["audio"]) for s in stems.values())
		if max_len <= 0:
			return

		target_points = 500
		mix = np.zeros(max_len, dtype=np.float32)
		for s in stems.values():
			audio = s["audio"]
			if len(audio) > 0:
				mix[:len(audio)] += audio.astype(np.float32) * s.get("volume", 1.0)

		step = max(1, len(mix) // target_points)
		envelope = np.zeros(target_points)
		for i in range(target_points):
			start = i * step
			end = min(start + step, len(mix))
			segment = mix[start:end]
			if len(segment) > 0:
				envelope[i] = np.max(np.abs(segment))

		peak = np.max(envelope)
		if peak > 0:
			envelope /= peak
		self.seek_slider.set_waveform(envelope)

	def _setup_ui(self):
		layout = QVBoxLayout(self)
		layout.setSpacing(12)
		layout.setContentsMargins(16, 16, 16, 16)
		self._build_playback_bar(layout)
		self._build_table(layout)
		self._build_buttons(layout)

	def _build_playback_bar(self, parent_layout):
		playback_layout = QHBoxLayout()
		self.play_btn = QPushButton("▶")
		self.play_btn.setFixedSize(40, 32)
		self.play_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.ACCENT_SUCCESS};
				color: #FFFFFF;
				border: none;
				border-radius: {theme.BORDER_RADIUS_SM};
				font-weight: bold;
				font-size: 16px;
			}}
			QPushButton:hover {{ background-color: #66BB6A; }}
		""")
		self.play_btn.clicked.connect(self._toggle_playback)
		playback_layout.addWidget(self.play_btn)

		self.seek_slider = WaveformSlider()
		self.seek_slider.setRange(0, 1000)
		self.seek_slider.setValue(0)
		self.seek_slider.setStyleSheet("QSlider { background: transparent; }")
		self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
		self.seek_slider.sliderReleased.connect(self._on_seek_released)
		self.seek_slider.valueChanged.connect(self._on_seek_value_changed)
		playback_layout.addWidget(self.seek_slider, stretch=1)

		self.time_label = QLabel("00:00 / 00:00")
		self.time_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px;")
		playback_layout.addWidget(self.time_label)
		parent_layout.addLayout(playback_layout)

	def _build_table(self, parent_layout):
		self.table = QTableWidget()
		self.table.setColumnCount(4)
		self.table.setHorizontalHeaderLabels(["Seccion", "Inicio (s)", "Fin (s)", ""])
		h = self.table.horizontalHeader()
		h.setStretchLastSection(False)
		h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
		h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
		h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
		h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
		self.table.setColumnWidth(1, 122)
		self.table.setColumnWidth(2, 122)
		self.table.setColumnWidth(3, 60)
		self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
		self.table.verticalHeader().setDefaultSectionSize(28)
		self.table.setStyleSheet(f"""
			QTableWidget {{
				background-color: {theme.BG_SECONDARY};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BG_TERTIARY};
				border-radius: {theme.BORDER_RADIUS_SM};
				gridline-color: {theme.BG_TERTIARY};
			}}
			QTableWidget::item {{ padding: 2px 6px; }}
			QHeaderView::section {{
				background-color: {theme.BG_TERTIARY};
				color: {theme.TEXT_MUTED};
				padding: 6px;
				border: none;
				font-weight: bold;
			}}
		""")
		parent_layout.addWidget(self.table, stretch=1)

	def _build_buttons(self, parent_layout):
		btn_layout = QHBoxLayout()
		self.add_btn = QPushButton("+ Anadir seccion")
		self.add_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.ACCENT_INFO};
				color: #FFFFFF;
				border: none;
				border-radius: {theme.BORDER_RADIUS_SM};
				padding: 6px 14px;
				font-weight: bold;
			}}
			QPushButton:hover {{ background-color: #42A5F5; }}
		""")
		self.add_btn.clicked.connect(self._add_section)
		btn_layout.addWidget(self.add_btn)

		btn_layout.addStretch()

		self.cancel_btn = QPushButton("Cancelar")
		self.cancel_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.BG_TERTIARY};
				color: {theme.TEXT_PRIMARY};
				border: none;
				border-radius: {theme.BORDER_RADIUS_SM};
				padding: 6px 14px;
			}}
			QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
		""")
		self.cancel_btn.clicked.connect(self.close)
		btn_layout.addWidget(self.cancel_btn)

		self.save_btn = QPushButton("Guardar")
		self.save_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.ACCENT_SUCCESS};
				color: #FFFFFF;
				border: none;
				border-radius: {theme.BORDER_RADIUS_SM};
				padding: 6px 14px;
				font-weight: bold;
			}}
			QPushButton:hover {{ background-color: #66BB6A; }}
		""")
		self.save_btn.clicked.connect(self._save)
		btn_layout.addWidget(self.save_btn)
		parent_layout.addLayout(btn_layout)

	def _spin_value(self, row, col):
		spin = self.table.cellWidget(row, col)
		return spin.value() if spin else 0.0

	def _set_spin(self, row, col, value):
		spin = self.table.cellWidget(row, col)
		if spin:
			spin.blockSignals(True)
			spin.setValue(round(value, 2))
			spin.blockSignals(False)

	def _on_start_changed(self, row):
		value = self._spin_value(row, 1)
		if row > 0:
			self._set_spin(row - 1, 2, value)
		self._update_marks()
		self._update_button_states()

	def _on_end_changed(self, row):
		value = self._spin_value(row, 2)
		if row + 1 < self.table.rowCount():
			self._set_spin(row + 1, 1, value)
		self._update_marks()
		self._update_button_states()

	def _update_button_states(self):
		total_s = self._get_total_seconds()
		for r in range(self.table.rowCount()):
			start_spin = self.table.cellWidget(r, 1)
			end_spin = self.table.cellWidget(r, 2)
			if start_spin and end_spin:
				start_spin.set_decrement_enabled(r > 0 or start_spin.value() > 0.001)
				end_spin.set_increment_enabled(
					r + 1 < self.table.rowCount() or
					(total_s > 0 and end_spin.value() + end_spin._step < total_s)
				)

	def _get_total_samples(self):
		stems = self.controller.state.stems
		if not stems:
			return 0
		max_len = max(len(s["audio"]) for s in stems.values())
		bpm = self.controller.state.detected_bpm or 120
		mix_sr = self.controller.state.mix_sr
		beats_per_bar = 4
		count_in_beats = self.controller.state.count_in_bars * beats_per_bar
		count_in_samples = int(count_in_beats * mix_sr * 60 / bpm) if count_in_beats > 0 else 0
		return max_len + count_in_samples

	def _get_total_seconds(self):
		total_samples = self._get_total_samples()
		mix_sr = self.controller.state.mix_sr
		if total_samples <= 0 or mix_sr <= 0:
			return 0
		return total_samples / mix_sr

	def _load_sync(self):
		self.table.setRowCount(0)
		if not os.path.exists(self.sync_path):
			return
		try:
			with open(self.sync_path, 'r', encoding='utf-8') as f:
				sync_data = json.load(f)
		except Exception as e:
			QMessageBox.critical(self, "Error", f"No se pudo leer sync.json:\n{e}")
			return

		sections = sync_data.get("sections", [])
		for sec in sections:
			self._add_row(sec.get("label", ""), float(sec.get("start", 0)), float(sec.get("end", 10)))
		self._update_marks()
		self._update_button_states()

	def _add_row(self, label="Nueva seccion", start=0.0, end=10.0):
		row = self.table.rowCount()
		self.table.insertRow(row)

		name_item = QTableWidgetItem(label)
		self.table.setItem(row, 0, name_item)

		start_spin = SpinBoxWidget()
		start_spin.setRange(0, 999999)
		start_spin.setDecimals(2)
		start_spin.setSingleStep(0.5)
		start_spin.setValue(round(start, 2))
		start_spin.valueChanged.connect(lambda val, w=start_spin: self._on_start_changed(self._row_of_widget(w, 1)))
		self.table.setCellWidget(row, 1, start_spin)

		end_spin = SpinBoxWidget()
		end_spin.setRange(0, 999999)
		end_spin.setDecimals(2)
		end_spin.setSingleStep(0.5)
		end_spin.setValue(round(end, 2))
		end_spin.valueChanged.connect(lambda val, w=end_spin: self._on_end_changed(self._row_of_widget(w, 2)))
		self.table.setCellWidget(row, 2, end_spin)

		del_btn = QPushButton("✕")
		del_btn.setFixedSize(32, 28)
		del_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.ACCENT_DANGER_ALT};
				color: #FFFFFF;
				border: none;
				border-radius: {theme.BORDER_RADIUS_SM};
				font-weight: bold;
			}}
			QPushButton:hover {{ background-color: #FF3333; }}
		""")
		del_btn.clicked.connect(lambda checked=False, b=del_btn: self._delete_row(self._row_of_widget(b, 3)))
		self.table.setCellWidget(row, 3, del_btn)

	def _row_of_widget(self, widget, col):
		for r in range(self.table.rowCount()):
			if self.table.cellWidget(r, col) is widget:
				return r
		return -1

	def _delete_row(self, row):
		if row < 0 or row >= self.table.rowCount():
			return
		if self.table.rowCount() <= 1:
			QMessageBox.warning(self, "Error", "Debe haber al menos una seccion.")
			return
		self.table.removeRow(row)
		self._update_marks()
		self._update_button_states()

	def _add_section(self):
		last_end = 0.0
		for r in range(self.table.rowCount()):
			last_end = max(last_end, self._spin_value(r, 2))
		self._add_row("Nueva seccion", last_end, round(last_end + 10.0, 2))
		self._update_marks()
		self._update_button_states()

	def _get_sections_from_table(self):
		sections = []
		for r in range(self.table.rowCount()):
			name_item = self.table.item(r, 0)
			start = self._spin_value(r, 1)
			end = self._spin_value(r, 2)
			if name_item:
				name = name_item.text().strip()
				if not name:
					name = f"Seccion {r+1}"
				sections.append({"label": name, "start": start, "end": end})
		return sections

	def _validate_sections(self):
		sections = self._get_sections_from_table()
		if not sections:
			QMessageBox.warning(self, "Error", "Debe haber al menos una seccion.")
			return False
		for i, sec in enumerate(sections):
			if sec["end"] <= sec["start"]:
				QMessageBox.warning(self, "Error",
					f"'{sec['label']}': fin ({sec['end']}) <= inicio ({sec['start']}).")
				return False
		return True

	def _update_marks(self):
		sections = self._get_sections_from_table()
		total_s = self._get_total_seconds()
		if total_s <= 0:
			return
		marks = []
		for sec in sections:
			for pos in (int((sec["start"] / total_s) * 1000), int((sec["end"] / total_s) * 1000)):
				if 0 <= pos <= 1000:
					marks.append(pos)
		self.seek_slider.set_marks(marks)

	def _toggle_playback(self):
		controller = self.controller
		pt = controller.threads.playback_thread
		if pt and pt.is_playing:
			controller._pause_playback()
			self.play_btn.setText("▶")
		else:
			controller._start_playback()
			self.play_btn.setText("⏸")
			self._connect_progress()

	def _connect_progress(self):
		pt = self.controller.threads.playback_thread
		if pt:
			try:
				pt.update_progress.connect(self.update_progress, Qt.ConnectionType.UniqueConnection)
			except Exception:
				pass

	def _on_seek_pressed(self):
		self._ignore_progress = True

	def _on_seek_released(self):
		self._ignore_progress = False
		self._apply_seek()

	def _on_seek_value_changed(self, value):
		if self._ignore_progress:
			self._update_time_label(value)

	def _apply_seek(self):
		value = self.seek_slider.value()
		total_samples = self._get_total_samples()
		if total_samples <= 0:
			return
		absolute_pos = int((value / 1000.0) * total_samples)
		controller = self.controller
		pt = controller.threads.playback_thread
		if pt and pt.isRunning():
			pt.seek(absolute_pos)
		else:
			controller._pending_seek = absolute_pos
		self._update_time_label(value)

	def _update_time_label(self, slider_value):
		total_seconds = self._get_total_seconds()
		if total_seconds <= 0:
			self.time_label.setText("00:00 / 00:00")
			return
		current_seconds = int((slider_value / 1000.0) * total_seconds)
		cur_min, cur_sec = divmod(current_seconds, 60)
		total_min, total_sec = divmod(int(total_seconds), 60)
		self.time_label.setText(f"{cur_min:02d}:{cur_sec:02d} / {total_min:02d}:{total_sec:02d}")

	def _highlight_section_at_time(self, seconds):
		sections = self._get_sections_from_table()
		found = -1
		for i, sec in enumerate(sections):
			if sec["start"] <= seconds < sec["end"]:
				found = i
				break

		for r in range(self.table.rowCount()):
			if r == found:
				bg = QColor(theme.ACCENT_PRIMARY)
				bg.setAlpha(40)
			elif r % 2 == 0:
				bg = QColor(theme.BG_SECONDARY)
			else:
				bg = QColor(theme.BG_TERTIARY).lighter(110)
			for c in range(self.table.columnCount()):
				item = self.table.item(r, c)
				if item:
					item.setBackground(bg)

	def update_progress(self, value: float):
		if self._ignore_progress:
			return
		self.seek_slider.blockSignals(True)
		self.seek_slider.setValue(int(value * 1000))
		self.seek_slider.blockSignals(False)
		self._update_time_label(int(value * 1000))

		total_seconds = self._get_total_seconds()
		if total_seconds > 0:
			self._highlight_section_at_time(value * total_seconds)

	def _save(self):
		if not self._validate_sections():
			return
		sections = self._get_sections_from_table()
		sync_data = {"sections": sections}
		try:
			with open(self.sync_path, 'w', encoding='utf-8') as f:
				json.dump(sync_data, f, indent=2, ensure_ascii=False)
		except OSError as e:
			QMessageBox.critical(self, "Error", f"No se pudo guardar sync.json:\n{e}")
			return

		self.controller.live_display_widget.load_sync_data(self.chopro_path, self.sync_path)
		self.controller.status_label.setText("Sync actualizado.")
		self.saved.emit()

	def closeEvent(self, event):
		controller = self.controller
		pt = controller.threads.playback_thread
		if pt and pt.is_playing:
			controller._pause_playback()
		super().closeEvent(event)

	def showEvent(self, event):
		super().showEvent(event)
		self._connect_progress()
