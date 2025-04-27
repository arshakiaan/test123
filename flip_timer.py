import sys
import math
import datetime # Для расчета времени срабатывания будильника
import time # Для получения текущего текущего времени
import os

# PyQt imports
from PyQt5.QtCore import (
    Qt, QTimer, QRectF, QPoint, QTime, QSize, QRect,
    QEasingCurve, QPropertyAnimation, QVariantAnimation, QAbstractAnimation,
    pyqtProperty, QDateTime, pyqtSignal, QEvent # Добавлен QEvent
)
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath, QIcon,
    QFontDatabase, QFontMetrics, QPixmap
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QSpacerItem, QFrame, QStackedWidget,
    QMessageBox # Для сообщений
)

# Pygame import for sound
import pygame

# --- Define Timer States ---
class TimerState:
    IDLE = 0      # Setting time (Picker view)
    RUNNING = 1   # Timer is counting down (Display view)
    PAUSED = 2    # Timer is paused (Display view)
    FINISHED = 3  # Timer has finished (Display view)


# --- Custom iOS Style Toggle Switch Widget ---
class IOSToggleSwitch(QWidget):
    # Signal emitted when the switch state changes
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(51, 31) # Standard iOS toggle size

        self._checked = False # Initial state is OFF
        self._slider_position = 0.0 # 0.0 for OFF, 1.0 for ON

        # Animation for smooth transition
        self._animation = QPropertyAnimation(self, b'slider_position')
        self._animation.setDuration(200) # Animation duration in ms
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)

    # Property for animating slider position
    @pyqtProperty(float)
    def slider_position(self):
        return self._slider_position

    @slider_position.setter
    def slider_position(self, pos):
        self._slider_position = pos
        self.update() # Redraw the widget

    def is_checked(self):
        return self._checked

    def set_checked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self._animation.stop()
            if self._checked:
                self._animation.setStartValue(self._slider_position)
                self._animation.setEndValue(1.0)
            else:
                self._animation.setStartValue(self._slider_position)
                self._animation.setEndValue(0.0)
            self._animation.start()
            self.toggled.emit(self._checked) # Emit signal

    def toggle(self):
        self.set_checked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        radius = rect.height() / 2 # Half of the height for rounded corners

        # Draw the background track
        # Color is green when ON, light grey when OFF
        if self._checked:
            background_color = QColor(76, 217, 100) # iOS Green
        else:
            background_color = QColor(189, 189, 191) # Light Grey

        painter.setBrush(background_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        # Draw the slider handle
        handle_size = rect.height() - 4 # Slightly smaller than height
        handle_rect = QRectF(0, 0, handle_size, handle_size)
        handle_rect.moveCenter(rect.center())

        # Calculate horizontal position based on slider_position (0.0 to 1.0)
        # Move from left side (padding 2) to right side (padding 2)
        min_x = rect.left() + 2
        max_x = rect.right() - handle_size - 2
        current_x = min_x + (max_x - min_x) * self._slider_position
        handle_rect.moveLeft(current_x)

        painter.setBrush(QColor(255, 255, 255)) # White handle
        # Add a subtle shadow (optional, requires more complex drawing or QGraphicsEffect)
        # For simplicity, we'll skip the shadow here.
        painter.drawEllipse(handle_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle() # Toggle the state on click
            event.accept()

    # Override enterEvent and leaveEvent to prevent hover effects
    # The user requested no visual change on hover for the toggle itself.
    # However, the parent window's transparency changes based on mouse position
    # over the *entire* window, which is handled in TimerApp's eventFilter.
    # So, we keep these methods as they were to prevent hover effects *on the toggle widget itself*.
    def enterEvent(self, event):
        event.ignore() # Ignore enter events

    def leaveEvent(self, event):
        event.ignore() # Ignore leave events


# --- Custom Title Bar Widget ---
class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.setFixedHeight(30) # Фиксированная высота строки заголовка
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.1); /* Слегка прозрачный фон */
                border-top-left-radius: 20px; /* Закругляем верхние углы */
                border-top-right-radius: 20px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                color: #CCCCCC; /* Светло-серый цвет кнопок */
                padding: 5px;
            }
            QPushButton:hover {
                color: white; /* Белый при наведении */
            }
            QPushButton:pressed {
                color: #AAAAAA; /* Темнее серый при нажатии */
            }
            QLabel {
                color: #CCCCCC; /* Светло-серый цвет текста */
                font-size: 14px;
                font-weight: bold;
                padding-left: 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.title_label = QLabel(self._parent.windowTitle() if self._parent else "Timer")
        layout.addWidget(self.title_label, 1) # Заголовок занимает максимум места

        # --- Add the Toggle Switch ---
        self.transparent_toggle = IOSToggleSwitch(self)
        layout.addWidget(self.transparent_toggle, alignment=Qt.AlignVCenter)
        # -----------------------------

        self.minimize_button = QPushButton("-")
        self.minimize_button.clicked.connect(self.minimize_window)
        self.minimize_button.setFixedSize(25, 25)
        layout.addWidget(self.minimize_button)

        self.close_button = QPushButton("X")
        self.close_button.clicked.connect(self.close_window)
        self.close_button.setFixedSize(25, 25)
        layout.addWidget(self.close_button)

        # For dragging
        self._drag_position = None

    def mousePressEvent(self, event):
        # This method handles dragging the window.
        # When transparent mode is ON, the main window's eventFilter
        # will pass mouse events *within* the title bar to this widget.
        # So, this dragging logic should still work correctly.
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self._parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_position is not None:
            self._parent.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_position is not None:
            self._drag_position = None
            event.accept()

    def minimize_window(self):
        if self._parent:
            self._parent.showMinimized()

    def close_window(self):
        if self._parent:
            self._parent.close()


# --- Custom widget for a single time "wheel" picker ---
class PickerWheel(QWidget):
    # Signal can be useful to notify about selected value changes
    # value_changed = pyqtSignal(int) # If emitting a signal is needed

    def __init__(self, value_range, unit_label, parent=None):
        super().__init__(parent)
        self.value_range = value_range # Value range (e.g., 0-23 or 0-59)
        self.unit_label = unit_label # Label (e.g., "hours", "min")

        self._values = list(range(self.value_range[0], self.value_range[1] + 1))
        # Add some values at the beginning and end for the infinite scroll effect (visually)
        padding_values = 10 # Increase padding for better visual effect
        extended_start = list(range(self.value_range[1] - padding_values + 1, self.value_range[1] + 1))
        extended_end = list(range(self.value_range[0], self.value_range[0] + padding_values))
        self._values = extended_start + self._values + extended_end

        # Индекс центрального элемента в _values, который соответствует значению value_range[0]
        self.current_value_index = padding_values # Индекс первого элемента из исходного диапазона

        self._y_offset = 0.0 # Смещение для прокрутки (в пикселях), используем float для плавной анимации

        self._dragging = False
        self._last_mouse_pos = QPoint()
        self._velocity = 0.0 # Для имитации инерции
        self._animation_timer = QTimer(self) # Таймер для анимации инерции
        self._animation_timer.timeout.connect(self._apply_inertia)

        self.item_height = 40 # Ориентировочная высота одного элемента в списке (будет пересчитана в paintEvent)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(50) # Минимальная ширина для колесика
        self.setMouseTracking(True) # Включаем отслеживание мыши даже без нажатия для потенциальной инерции

    # Свойство для анимации y_offset
    @pyqtProperty(float)
    def y_offset(self):
        return self._y_offset

    @y_offset.setter
    def y_offset(self, offset):
        self._y_offset = offset
        self.update() # Перерисовываем при изменении позиции


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        rect = self.rect()
        center_y = rect.center().y()

        # Шрифт для чисел. Применяем шрифт из QApplication.
        font = QApplication.font()
        # Базовый размер шрифта для центральных элементов (крупный)
        base_font_size = 15
        font.setPointSize(base_font_size)
        # Получаем метрики шрифта для расчета высоты элементов
        font_metrics = QFontMetrics(font)

        # Высота одного элемента (высота текста + отступ)
        self.item_height = font_metrics.height() * 1.2 # Отступ 20% от высоты текста

        # Вычисляем индекс элемента, который сейчас должен быть по центру
        # Исходя из текущего смещения и высоты элемента
        # Этот расчет нужен только для отрисовки и эффектов прозрачности/масштаба
        # Реальный selected_value определяется после остановки прокрутки
        effective_central_index = self.current_value_index - self._y_offset / self.item_height


        # Определяем диапазон индексов элементов, которые попадают в видимую область виджета
        visible_range_start = max(0, int(effective_central_index - rect.height() / self.item_height / 2) - 5)
        visible_range_end = min(len(self._values), int(effective_central_index + rect.height() / self.item_height / 2) + 5)


        # Рисуем числа
        for i in range(visible_range_start, visible_range_end):
            value = self._values[i]
            # Вычисляем вертикальную позицию центра числа
            # Позиция рассчитывается относительно центра виджета
            item_center_y = center_y + (i - effective_central_index) * self.item_height


            # Расстояние от центра виджета до центра текущего числа (абсолютное значение)
            distance_to_center = abs(item_center_y - center_y)

            # Вычисляем прозрачность и размер шрифта в зависимости от расстояния
            # Используем кривую (степень) для плавного эффекта расфокуса
            max_distance = rect.height() / 2 # Максимальное расстояние от центра до края виджета
            # Нормализованное расстояние (от 0 до 1), ограничиваем, чтобы эффект не был слишком резким
            normalized_distance = min(1.0, distance_to_center / (max_distance * 0.8)) # Множитель 0.8 для более выраженного центра

            # Прозрачность: 1.0 в центре, уменьшается к краям
            # Используем степень для более плавного перехода opacity = (1 - normalized_distance)^power
            power = 2.0 # Степень для плавности
            opacity = math.pow((1.0 - normalized_distance), power)
            opacity = max(0.3, opacity) # Минимальная прозрачность 30%


            # Размер шрифта: больше в центре, меньше к краям
            # Масштаб шрифта: 1.0 в центре, уменьшается к краям
            font_scale = 1.0 - normalized_distance * 0.3 # Уменьшаем размер до 70% на краю
            font_scale = max(0.7, font_scale) # Минимальный размер 70%
            current_font_size = int(base_font_size * font_scale)
            if current_font_size <= 0: current_font_size = 1 # Минимальный размер шрифта 1

            # Устанавливаем цвет с учетом прозрачности
            color = QColor(255, 255, 255) # Белый
            color.setAlphaF(opacity) # Применяем прозрачность
            painter.setPen(color)

            # Устанавливаем размер шрифта для текущего элемента
            current_font = font
            current_font.setPointSize(current_font_size)
            painter.setFont(current_font)

            # Вычисляем прямоугольник для текста с учетом нового размера шрифта
            current_font_metrics = QFontMetrics(current_font)
            text_rect = current_font_metrics.boundingRect(str(value))
            text_x = rect.center().x() - text_rect.width() / 2 # Центрируем текст по горизонтали
            # Учитываем baseline для вертикального выравнивания
            text_y = item_center_y - text_rect.height() / 2 + current_font_metrics.ascent()


            # Рисуем число, только если оно попадает примерно в видимую область
            # Упрощенная проверка видимости
            if item_center_y > -self.item_height * 2 and item_center_y < rect.height() + self.item_height * 2:
                 painter.drawText(int(text_x), int(text_y), str(value))


        # (Опционально) Рисуем центральные линии или рамку для выделения выбранного значения
        painter.setPen(QPen(QColor(50, 50, 50, 150), 1)) # Темно-серые полупрозрачные линии
        line_y_top = center_y - self.item_height / 2
        line_y_bottom = center_y + self.item_height / 2
        painter.drawLine(rect.left(), int(line_y_top), rect.right(), int(line_y_top))
        painter.drawLine(rect.left(), int(line_y_bottom), rect.right(), int(line_y_bottom))


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_mouse_pos = event.pos()
            self._velocity = 0.0 # Сбрасываем скорость при начале перетаскивания
            self._animation_timer.stop() # Останавливаем анимацию инерции
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._dragging:
            delta_y = event.pos().y() - self._last_mouse_pos.y()
            self._y_offset += delta_y
            # Обновляем скорость (простая оценка)
            # В реальной инерции нужно учитывать время между событиями
            self._velocity = delta_y # В упрощенной модели скорость = смещение
            self.update() # Перерисовываем для отображения движения
            self._last_mouse_pos = event.pos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            # --- Логика "прилипания" и инерции ---
            # Если была достаточная скорость, запускаем анимацию инерции
            if abs(self._velocity) > 1.0: # Порог скорости для инерции
                 self._animation_timer.start(16) # Запускаем таймер анимации (60 FPS)
            else:
                 # Иначе сразу "прилипаем" к ближайшему значению
                 self._snap_to_nearest_item()

            event.accept()

    def _apply_inertia(self):
        """Применяет скорость и замедление для имитации инерции."""
        self._y_offset += self._velocity
        self._velocity *= 0.95 # Коэффициент замедления (например, 5% за кадр)

        # Если скорость стала очень маленькой, останавливаем анимацию и прилипаем
        if abs(self._velocity) < 1.0:
            self._animation_timer.stop()
            self._snap_to_nearest_item()

        self.update() # Перерисовываем для отображения движения

    def _snap_to_nearest_item(self):
        """Прилипает к ближайшему элементу после остановки прокрутки."""
        rect = self.rect()
        center_y = rect.center().y()

        # Вычисляем индекс элемента, который сейчас находится ближе всего к центру
        # Исходя из общего смещения от исходного центрального элемента
        # Индекс центрального элемента при _y_offset = 0 это self.current_value_index (исходный)
        # Смещение в элементах = -_y_offset / item_height
        items_scrolled_float = -self._y_offset / self.item_height
        items_to_snap = round(items_scrolled_float)

        # Новый индекс выбранного значения в расширенном списке
        new_current_value_index_in_extended_list = self.current_value_index + items_to_snap

        # Корректируем индекс, чтобы он всегда указывал на элемент в расширенном списке
        # Если анимация инерции привела к выходу за границы, возвращаем в допустимый диапазон
        new_current_value_index_in_extended_list = max(0, min(len(self._values) - 1, new_current_value_index_in_extended_list))


        # Вычисляем целевое смещение _y_offset для анимации прилипания
        # Оно должно быть таким, чтобы элемент с новым индексом оказался ровно по центру
        target_y_offset = -(new_current_value_index_in_extended_list - self.current_value_index) * self.item_height

        # Запускаем анимацию "прилипания"
        self.snap_animation = QPropertyAnimation(self, b'y_offset')
        self.snap_animation.setStartValue(self._y_offset)
        self.snap_animation.setEndValue(target_y_offset)
        self.snap_animation.setDuration(min(300, int(abs(self._y_offset - target_y_offset) * 2))) # Длительность зависит от расстояния
        self.snap_animation.setEasingCurve(QEasingCurve.OutQuad)
        self.snap_animation.finished.connect(self._snap_animation_finished)
        self.snap_animation.start()

        # Обновляем индекс выбранного значения после определения цели анимации
        self.current_value_index = new_current_value_index_in_extended_list


    def _snap_animation_finished(self):
          # После анимации прилипания сбрасываем смещение _y_offset в ноль.
          self._y_offset = 0.0
          self.update()
          # Теперь self.current_value_index точно указывает на выбранный элемент
          # Можно издать сигнал, если нужно: self.value_changed.emit(self.get_selected_value())
          # print(f"Picker '{self.unit_label}' snapped to: {self.get_selected_value()}")


    def get_selected_value(self):
          """Возвращает текущее выбранное значение (из исходного диапазона)."""
          # Нужно взять значение по текущему индексу current_value_index
          # и учесть цикличность, если мы вышли за пределы исходного диапазона
          if 0 <= self.current_value_index < len(self._values):
              # Вычисляем реальное значение в пределах исходного диапазона value_range
              num_values_in_range = self.value_range[1] - self.value_range[0] + 1
              value_in_extended_list = self._values[self.current_value_index]

              # Используем оператор % для циклической прокрутки значений
              # Сначала приводим к 0-based индексу в исходном диапазоне
              zero_based_value = value_in_extended_list - self.value_range[0]
              # Применяем цикличность и приводим обратно к исходному диапазону
              real_value = (zero_based_value % num_values_in_range + num_values_in_range) % num_values_in_range + self.value_range[0]

              return real_value

          return self.value_range[0] # Возвращаем минимальное значение по умолчанию

    def set_value(self, value):
        """Устанавливает выбранное значение и центрирует колесико."""
        # Находим индекс этого значения в исходном списке
        try:
            initial_list_index = list(range(self.value_range[0], self.value_range[1] + 1)).index(value)
            # Вычисляем соответствующий индекс в расширенном списке (с учетом padding)
            # padding_values = 10
            index_in_extended_list = initial_list_index + 10

            if 0 <= index_in_extended_list < len(self._values):
                 self.current_value_index = index_in_extended_list
                 self._y_offset = 0.0 # Сбрасываем любое текущее смещение
                 self.update() # Перерисовываем
        except ValueError:
            print(f"Warning: Value {value} is out of range {self.value_range} for {self.unit_label} picker.")
            # Можно установить на минимальное или максимальное значение


# --- Custom widget to assemble wheels and labels ---
class TimePickerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) # Убираем расстояние между колесиками

        # Создаем колесики для часов, минут и секунд
        self.hours_wheel = PickerWheel((0, 23), "hours", self)
        self.minutes_wheel = PickerWheel((0, 59), "min", self)
        self.seconds_wheel = PickerWheel((0, 59), "sec", self)

        # Макет для каждого колесика с его меткой
        hours_layout = QVBoxLayout()
        hours_layout.setContentsMargins(0, 0, 0, 0)
        hours_layout.setSpacing(5)
        hours_layout.addWidget(self.hours_wheel, 1) # Колесико занимает основное место
        hours_label = QLabel("hours", self)
        hours_label.setStyleSheet("color: #8A8A8E; font-size: 14px; background: transparent; qproperty-alignment: AlignCenter;")
        hours_layout.addWidget(hours_label, alignment=Qt.AlignTop | Qt.AlignCenter) # Метка внизу

        minutes_layout = QVBoxLayout()
        minutes_layout.setContentsMargins(0, 0, 0, 0)
        minutes_layout.setSpacing(5)
        minutes_layout.addWidget(self.minutes_wheel, 1)
        minutes_label = QLabel("min", self)
        minutes_label.setStyleSheet("color: #8A8A8E; font-size: 14px; background: transparent; qproperty-alignment: AlignCenter;")
        minutes_layout.addWidget(minutes_label, alignment=Qt.AlignTop | Qt.AlignCenter)

        seconds_layout = QVBoxLayout()
        seconds_layout.setContentsMargins(0, 0, 0, 0)
        seconds_layout.setSpacing(5)
        seconds_layout.addWidget(self.seconds_wheel, 1)
        seconds_label = QLabel("sec", self)
        seconds_label.setStyleSheet("color: #8A8A8E; font-size: 14px; background: transparent; qproperty-alignment: AlignCenter;")
        seconds_layout.addWidget(seconds_label, alignment=Qt.AlignTop | Qt.AlignCenter)

        # Добавляем макеты колесиков в основной горизонтальный макет с разделителями (опционально)
        main_layout.addLayout(hours_layout, 1)
        main_layout.addLayout(minutes_layout, 1)
        main_layout.addLayout(seconds_layout, 1)

        self.setLayout(main_layout)

    def get_time(self):
        """Возвращает выбранное время как объект QTime."""
        hours = self.hours_wheel.get_selected_value()
        minutes = self.minutes_wheel.get_selected_value()
        seconds = self.seconds_wheel.get_selected_value()
        # Убедимся, что значения в пределах допустимого для QTime
        hours = max(0, min(23, hours))
        minutes = max(0, min(59, minutes))
        seconds = max(0, min(59, seconds))
        return QTime(hours, minutes, seconds)

    def set_time(self, time_obj: QTime):
        """Устанавливает время в колесиках выбора."""
        self.hours_wheel.set_value(time_obj.hour())
        self.minutes_wheel.set_value(time_obj.minute())
        self.seconds_wheel.set_value(time_obj.second())


# --- Widget for displaying the countdown timer ---
class TimerDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Добавляем отступы вокруг содержимого виджета отображения таймера
        main_layout = QVBoxLayout(self)
        # Уменьшим отступы для более компактного размещения
        main_layout.setContentsMargins(10, 110, 10, 10)
        main_layout.setSpacing(10) # Space between time digits and alarm info

        # Label for large countdown digits
        self.time_label = QLabel("00:00", self) # Will display HH:MM or MM:SS
        # Размер шрифта будет установлен динамически в resizeEvent
        self.time_label.setStyleSheet("""
            QLabel {
                color: white;
                background: transparent;
                /* font-size will be set in resizeEvent */
                font-family: 'SF Pro Display', 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
                qproperty-alignment: AlignCenter;
            }
        """)
        self.time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.time_label, alignment=Qt.AlignCenter)

        # Widget for alarm icon and trigger time (use QHBoxLayout for horizontal arrangement)
        alarm_info_widget = QWidget(self)
        alarm_info_layout = QHBoxLayout(alarm_info_widget)
        alarm_info_layout.setContentsMargins(0, 0, 0, 0)
        alarm_info_layout.setSpacing(5)
        alarm_info_layout.addStretch(1) # Push content to center

        # Alarm icon (using a character for simplicity, replace with QPixmap if needed)
        self.alarm_icon_label = QLabel("🔔", self) # Using a bell emoji character
        # Размер шрифта будет установлен динамически в resizeEvent
        self.alarm_icon_label.setStyleSheet("""
            QLabel {
                color: #FFA500; /* Orange color for icon */
                background: transparent;
                /* font-size will be set in resizeEvent */
            }
        """)
        # Check if a system emoji font is available or use a fallback character
        # Font will be set in resizeEvent
        self.alarm_time_label = QLabel("1:41 PM", self) # Example time
        # Размер шрифта будет установлен динамически в resizeEvent
        self.alarm_time_label.setStyleSheet("""
            QLabel {
                color: rgba(138, 138, 142, 0.7); /* Gray color with transparency */
                background: transparent;
                 /* font-size will be set in resizeEvent */
                font-family: 'SF Pro Text', sans-serif;
            }
        """)

        alarm_info_layout.addWidget(self.alarm_icon_label, alignment=Qt.AlignVCenter)
        alarm_info_layout.addWidget(self.alarm_time_label, alignment=Qt.AlignVCenter)
        alarm_info_layout.addStretch(1) # Push content to center

        main_layout.addWidget(alarm_info_widget, alignment=Qt.AlignCenter)

        # Добавляем немного растяжителя внизу, чтобы элементы были чуть выше центра
        main_layout.addStretch(1)

        self.setLayout(main_layout)

    def update_time_display(self, time_str, alarm_trigger_time_str):
        """Updates the countdown and alarm time labels."""
        self.time_label.setText(time_str)
        self.alarm_time_label.setText(alarm_trigger_time_str)

    def set_time_font_size(self, size):
        """Sets the font size of the large time digits."""
        font = self.time_label.font()
        font.setPointSize(size)
        self.time_label.setFont(font)

    def set_alarm_info_font_size(self, size):
          """Sets the font size of the alarm info text."""
          font = self.alarm_time_label.font()
          font.setPointSize(size)
          self.alarm_time_label.setFont(font)
          # Also scale the icon slightly with the text
          icon_font = self.alarm_icon_label.font()
          icon_font.setPointSize(int(size * 1.3)) # Icon slightly larger than text
          self.alarm_icon_label.setFont(icon_font)


# --- Main application window ---
class TimerApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("iOS Style Timer")
        # Убираем стандартную строку заголовка Windows
        # Оставляем WindowStaysOnTopHint, если нужно, чтобы окно всегда было поверх других
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")

        # Adjusted initial and minimum window sizes (slightly reduced)
        self.initial_width = 380 # Slightly reduced width
        self.initial_height = 480 # Slightly reduced height
        self.setGeometry(100, 100, self.initial_width, self.initial_height)
        self.setMinimumSize(280, 380) # Reduced minimum size
        # Save initial aspect ratio
        self.aspect_ratio = self.initial_width / self.initial_height

        self.corner_radius = 20

        # For window dragging (now handled by CustomTitleBar)
        # self.drag_position = None # Removed as not used here

        # Состояние раскрытия списка
        self.expanded = False
        self.expanded_section_height = 150

        # --- Timer Attributes ---
        # Timer for smooth animation updates (approx. 60 FPS)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_timer_animation)

        # Timer for actual countdown logic (every second)
        self.seconds_timer = QTimer(self)
        self.seconds_timer.timeout.connect(self.update_timer_logic)

        # Timer for colon blinking
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink_colon)
        self.colon_visible = True

        self.alarm_playing = False
        self.total_seconds_at_start = 0
        self.remaining_seconds = 0.0 # Use float for smoother progress calculation
        self.start_datetime = None # Use datetime for accurate time tracking
        self.end_datetime = None # To display alarm trigger time

        self.current_state = TimerState.IDLE # Start in picker state

        # Progress for the circular indicator (1.0 to 0.0, 1.0 means full circle)
        self.progress = 1.0

        # --- Transparency Mode Attribute ---
        self.transparent_mode_enabled = False
        # -----------------------------------

        self.create_ui()
        self.update_ui_state() # Set initial UI state

        # Save initial sizes and font sizes for scaling
        # Используем self.height() после создания UI, чтобы получить фактическую высоту
        self.initial_total_height = self.height()
        self.initial_width = self.width() # Сохраняем начальную ширину тоже
        # Вычисляем начальную высоту основной части окна (без нижней секции)
        # Это базовая высота для масштабирования по вертикали
        self.initial_main_height = self.initial_total_height - self.bottom_bar_frame.height() - (self.layout().contentsMargins().bottom() if self.layout() else 0)

        # Пересчитываем aspect_ratio на основе initial_main_height
        self.aspect_ratio = self.initial_width / self.initial_main_height # <-- Исправлено


        self.initial_button_font_size = 18
        # Initial font size for large timer digits and alarm info
        # Уменьшен начальный размер шрифта для цифр таймера (был 90)
        self.initial_display_time_font_size = int(80 / 2.7) # Уменьшено в 2.7 раза
        self.initial_alarm_info_font_size = 14 # Match size in TimerDisplayWidget

        # Сохраняем начальный размер кнопок для масштабирования
        self.initial_button_size = QSize(60, 60)

        # Install event filter to detect mouse movement over the window
        self.installEventFilter(self)


    def create_ui(self):
        main_layout = QVBoxLayout(self)
        # Reduce top margin to make space for the title bar
        main_layout.setContentsMargins(20, 0, 20, 10) # Reduced top margin
        main_layout.setSpacing(20)

        # --- Custom Title Bar ---
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)
        # Connect the toggle signal from the title bar
        self.title_bar.transparent_toggle.toggled.connect(self.toggle_transparent_mode)
        # ------------------------

        # --- Stacked Widget for Views ---
        self.stacked_widget = QStackedWidget(self)

        # View 0: Time Picker
        self.time_picker_widget = TimePickerWidget(self)
        self.time_picker_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.stacked_widget.addWidget(self.time_picker_widget) # Index 0

        # View 1: Timer Display
        self.timer_display_widget = TimerDisplayWidget(self)
        self.timer_display_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.stacked_widget.addWidget(self.timer_display_widget) # Index 1

        main_layout.addWidget(self.stacked_widget, 1)


        # --- Control Buttons Section ---
        self.buttons_layout = QHBoxLayout() # Сохраняем ссылку на макет кнопок
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(70) # Increased spacing


        # Style for round buttons with transparency
        button_base_style = """
            QPushButton {
                color: white; /* Text color */
                /* font-size will be set in resizeEvent */
                font-family: 'SF Pro Text', sans-serif;
                border-radius: 30px; /* Makes it round given fixed size */
                padding: 15px;
                /* min/max width/height will be set in resizeEvent */
            }
            QPushButton:disabled {
                background-color: rgba(51, 51, 51, 0.3);
                color: #777777;
            }
             QPushButton:pressed {
                 /* Add visual feedback for pressing */
                 background-color: rgba(85, 85, 85, 0.3);
             }
        """

        # Button Cancel
        self.cancel_button = QPushButton("Cancel")
        # Фон с прозрачностью: rgba(R, G, B, alpha)
        # Цвет #3A3A3C соответствует примерно RGB(58, 58, 60)
        self.cancel_button.setStyleSheet(button_base_style + """
            QPushButton { background-color: rgba(58, 58, 60, 0.3); } /* Dark grey with transparency */
             QPushButton:pressed { background-color: rgba(85, 85, 85, 0.3); } /* Чуть темнее серый */
        """)
        self.cancel_button.clicked.connect(self.cancel_timer)
        # Размеры будут установлены в resizeEvent
        # self.cancel_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


        # Button Start/Pause/Resume
        self.start_pause_button = QPushButton("Start")
          # Styles for different states will be set in update_ui_state
        self.start_pause_button.setStyleSheet(button_base_style)
        self.start_pause_button.clicked.connect(self.toggle_timer)
          # Размеры будут установлены в resizeEvent
        # self.start_pause_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


        self.buttons_layout.addStretch(1) # Pushes buttons to center
        self.buttons_layout.addWidget(self.cancel_button)
        self.buttons_layout.addWidget(self.start_pause_button)
        self.buttons_layout.addStretch(1)

        main_layout.addLayout(self.buttons_layout)

        # --- Expandable Section (keep as is) ---
        self.expandable_widget = QWidget(self)
        self.expandable_widget.setStyleSheet("background-color: #1C1C1E; border-radius: 8px;")
        expandable_layout = QVBoxLayout(self.expandable_widget)
        expandable_layout.setContentsMargins(15, 15, 15, 15)
        placeholder_label = QLabel("Список будет здесь (пока пусто)")
        placeholder_label.setStyleSheet("color: #8A8A8E; font-size: 14px; background: transparent;")
        placeholder_label.setAlignment(Qt.AlignCenter)
        expandable_layout.addWidget(placeholder_label)
        self.expandable_widget.setFixedHeight(self.expanded_section_height)
        self.expandable_widget.setVisible(False)

        # --- Bottom Bar with Toggle Button (keep as is) ---
        self.bottom_bar_frame = QFrame(self)
        self.bottom_bar_frame.setFrameShape(QFrame.NoFrame)
        bottom_bar_layout = QHBoxLayout(self.bottom_bar_frame)
        bottom_bar_layout.setContentsMargins(0, 5, 0, 0)
        bottom_bar_layout.setSpacing(0)
        self.toggle_button = QPushButton("^")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet("""
            QPushButton { color: #8A8A8E; background-color: transparent; border: none; font-size: 24px; font-weight: bold; padding: 0px; }
            QPushButton:hover { color: #CCCCCC; }
        """)
        self.toggle_button.setFixedSize(30, 30)
        self.toggle_button.clicked.connect(self.toggle_expandable_section)
        bottom_bar_layout.addWidget(self.toggle_button, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        bottom_bar_layout.addStretch(1)

        main_layout.addWidget(self.expandable_widget)
        main_layout.addWidget(self.bottom_bar_frame)

        self.setLayout(main_layout)

        # No need to connect picker wheel value changes to Start button state
        # unless we want the Start button to be disabled when time is 00:00:00 in picker view.
        # Let's keep it simple and check for 0 time in toggle_timer.


    def update_ui_state(self):
        """Updates widget visibility and button states based on current_state."""
        if self.current_state == TimerState.IDLE:
            self.stacked_widget.setCurrentIndex(0) # Show picker
            self.cancel_button.setEnabled(False) # Cancel disabled in IDLE
            # Start is enabled by default, check for 0 time in toggle_timer
            self.start_pause_button.setEnabled(True)
            self.start_pause_button.setText("Start")
            # Apply Start button style (Green with transparency)
            self.start_pause_button.setStyleSheet(self.styleSheet() + """
                QPushButton { background-color: rgba(50, 205, 50, 0.3); } /* Green with transparency */
                QPushButton:pressed { background-color: rgba(40, 164, 40, 0.3); }
            """)
            self.start_pause_button.setProperty("state", "") # Remove custom state property
            self.style().polish(self.start_pause_button) # Re-polish style
            self.progress = 1.0 # Reset progress for painting
            self.update() # Repaint to hide circle

        elif self.current_state == TimerState.RUNNING:
            self.stacked_widget.setCurrentIndex(1) # Show timer display
            self.cancel_button.setEnabled(True)
            self.start_pause_button.setEnabled(True)
            self.start_pause_button.setText("Pause")
            # Apply Pause button style (Orange with transparency)
            self.start_pause_button.setStyleSheet(self.styleSheet() + """
                QPushButton { background-color: rgba(255, 149, 0, 0.3); } /* Orange with transparency */
                QPushButton:pressed { background-color: rgba(224, 128, 0, 0.3); }
            """)
            self.start_pause_button.setProperty("state", "pause") # Set custom state property
            self.style().polish(self.start_pause_button)
            # Start animation timer (high frequency for smooth animation)
            self.animation_timer.start(16) # ~60 FPS
            # Start seconds timer for logic updates
            self.seconds_timer.start(1000)
            self.blink_timer.start(500) # Colon blinking
            self.colon_visible = True # Ensure colon is visible at start of RUNNING
            self.progress = 1.0 # Initial progress is full
            self.update() # Repaint to show circle

        elif self.current_state == TimerState.PAUSED:
            self.stacked_widget.setCurrentIndex(1) # Show timer display
            self.cancel_button.setEnabled(True)
            self.start_pause_button.setEnabled(True)
            self.start_pause_button.setText("Resume")
            # Pause button remains orange (style applied in RUNNING state)
            # Ensure style is applied if coming from FINISHED or other states
            if self.start_pause_button.property("state") != "pause":
                 self.start_pause_button.setStyleSheet(self.styleSheet() + """
                     QPushButton { background-color: rgba(255, 149, 0, 0.3); } /* Orange with transparency */
                     QPushButton:pressed { background-color: rgba(224, 128, 0, 0.3); }
                 """)
                 self.start_pause_button.setProperty("state", "pause")
                 self.style().polish(self.start_pause_button)

            self.animation_timer.stop() # Stop animation timer
            self.seconds_timer.stop() # Stop countdown logic
            self.blink_timer.stop() # Stop colon blinking
            self.colon_visible = True # Ensure colon is visible
            # Update display to show time with colon visible
            h = int(self.remaining_seconds) // 3600
            m = (int(self.remaining_seconds) % 3600) // 60
            s = int(self.remaining_seconds) % 60
            # Use current time format (HH:MM:SS or MM:SS)
            if self.total_seconds_at_start >= 3600:
                 time_str = f"{h:02}:{m:02}:{s:02}"
            else:
                 time_str = f"{m:02}:{s:02}"

            # Format alarm trigger time
            alarm_trigger_time_str = ""
            if self.end_datetime:
                 # Format as h:mm AP/PM
                 alarm_trigger_time_str = self.end_datetime.toString("h:mm AP").replace("AM", "am").replace("PM", "pm")

            self.timer_display_widget.update_time_display(time_str, alarm_trigger_time_str)
            self.update() # Repaint to ensure circle state is fixed and colon is visible


        elif self.current_state == TimerState.FINISHED:
            self.animation_timer.stop()
            self.seconds_timer.stop()
            self.blink_timer.stop()
            self.stacked_widget.setCurrentIndex(1) # Remain on display
            # Display 00:00, clear alarm time
            self.timer_display_widget.update_time_display("00:00", "")
            # --- CHANGE: Enable Cancel button in FINISHED state ---
            self.cancel_button.setEnabled(True) # Cancel IS needed to stop alarm and reset
            # -----------------------------------------------------------
            self.start_pause_button.setEnabled(True) # Start button should be enabled to start a new timer
            self.start_pause_button.setText("Start") # Button becomes Start
            # Apply Start button style
            self.start_pause_button.setStyleSheet(self.styleSheet() + """
                QPushButton { background-color: rgba(50, 205, 50, 0.3); } /* Green with transparency */
                QPushButton:pressed { background-color: rgba(40, 164, 40, 0.3); }
            """)
            self.start_pause_button.setProperty("state", "")
            self.style().polish(self.start_pause_button)
            self.progress = 0.0 # Progress is zero
            self.update() # Repaint to hide circle
            self.play_alarm() # Play sound
            # Optionally transition back to IDLE after a delay or user interaction

    def toggle_timer(self):
        """Handles Start, Pause, and Resume actions."""
        if self.current_state == TimerState.IDLE or self.current_state == TimerState.FINISHED:
            # --- CHANGE: Allow starting a new timer from FINISHED state ---
            # Get time from picker (or reset if starting from FINISHED)
            if self.current_state == TimerState.FINISHED:
                # If starting again after finished, ensure picker is reset or use last value?
                # Let's assume we start fresh from the picker's current value
                # Resetting the picker might be better UX, but let's stick to minimal changes
                # Stop alarm if it's still playing from the previous run
                self.stop_alarm_sound() # Ensure sound stops if Start is pressed while alarm plays

            selected_time = self.time_picker_widget.get_time()
            self.total_seconds_at_start = selected_time.hour() * 3600 + selected_time.minute() * 60 + selected_time.second()

            if self.total_seconds_at_start <= 0:
                print("Selected time is 0. Cannot start timer.")
                # Optionally show a message to the user
                QMessageBox.warning(self, "Warning", "Please set a time greater than 0.")
                return # Do not start if time is 0

            self.remaining_seconds = float(self.total_seconds_at_start) # Use float for smoother progress
            self.start_datetime = QDateTime.currentDateTime()
            self.end_datetime = self.start_datetime.addSecs(int(self.total_seconds_at_start))

            self.current_state = TimerState.RUNNING
            self.update_ui_state() # Switch to RUNNING state UI
            # ---------------------------------------------------------------------

        elif self.current_state == TimerState.RUNNING:
            # Pause
            self.current_state = TimerState.PAUSED
            self.update_ui_state() # Switch to PAUSED state UI

        elif self.current_state == TimerState.PAUSED:
            # Resume
            # When resuming, need to calculate remaining time more accurately
            # based on when it was paused. For simplicity, just restart from remaining_seconds.
            # A more accurate resume would involve storing the pause time.
            # Recalculate start_datetime to account for paused time
            now = QDateTime.currentDateTime()
            # The new start time should be 'now' minus the time that had already elapsed
            # elapsed_seconds_before_pause = self.total_seconds_at_start - self.remaining_seconds
            # self.start_datetime = now.addMSecs(-int(elapsed_seconds_before_pause * 1000))
            # Simpler: Recalculate end_datetime based on remaining seconds from now
            self.end_datetime = now.addSecs(int(round(self.remaining_seconds)))
            # We need a reference point for elapsed time calculation in update_timer_logic.
            # Let's adjust start_datetime so that the difference between now and start_datetime
            # reflects the time *already* passed.
            elapsed_seconds_so_far = self.total_seconds_at_start - self.remaining_seconds
            self.start_datetime = now.addMSecs(-int(elapsed_seconds_so_far * 1000))


            self.current_state = TimerState.RUNNING
            self.update_ui_state() # Switch to RUNNING state UI

        self.update() # Ensure UI updates after state change


    def cancel_timer(self):
        """Cancels the timer and returns to the time picker state."""
        self.animation_timer.stop()
        self.seconds_timer.stop()
        self.blink_timer.stop()

        # Stop sound if playing (important for cancelling from FINISHED state)
        self.stop_alarm_sound()

        # Reset time picker wheels to 00:00:00
        self.time_picker_widget.set_time(QTime(0, 0, 0))

        self.current_state = TimerState.IDLE
        self.update_ui_state()


    def stop_alarm_sound(self):
        """Stops the alarm sound if it's playing."""
        if self.alarm_playing:
            try:
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    print("Alarm sound stopped.")
            except pygame.error as e:
                print(f"Pygame error stopping music: {e}")
            finally:
                self.alarm_playing = False # Ensure flag is reset


    def update_timer_animation(self):
        """Updates the UI for smooth animation (called frequently)."""
        # This is called ~60 times per second.
        # We don't update the remaining seconds here, only trigger repaint for the circle.
        # The actual time update is in update_timer_logic.
        self.update() # Trigger paintEvent for smooth circle animation


    def update_timer_logic(self):
        """Updates the timer countdown logic (called every second)."""
        if self.start_datetime is None or self.current_state != TimerState.RUNNING:
             # Only update logic if running and started correctly
             return

        # Calculate elapsed time since start
        # Use floating point elapsed seconds for smoother progress calculation
        now = QDateTime.currentDateTime()
        elapsed_msecs = self.start_datetime.msecsTo(now)
        elapsed_seconds = elapsed_msecs / 1000.0

        # Calculate remaining seconds based on elapsed time
        self.remaining_seconds = max(0.0, float(self.total_seconds_at_start) - elapsed_seconds)

        # --- More robust check using end_datetime ---
        # remaining_msecs = now.msecsTo(self.end_datetime)
        # self.remaining_seconds = max(0.0, remaining_msecs / 1000.0)
        # --------------------------------------------

        if self.remaining_seconds <= 0.001: # Use a small threshold for floating point comparison
            self.remaining_seconds = 0.0 # Ensure it's exactly zero at the end
            self.current_state = TimerState.FINISHED
            self.update_ui_state()
            return

        # Update displayed time string (HH:MM:SS or MM:SS)
        # Display time based on rounded remaining seconds for the label
        display_seconds = int(math.ceil(self.remaining_seconds)) # Use ceil to show 00:01 until it hits 0
        h = display_seconds // 3600
        m = (display_seconds % 3600) // 60
        s = display_seconds % 60

        # Determine format based on total time at start
        if self.total_seconds_at_start >= 3600:
            # Show HH:MM:SS if original time was >= 1 hour
             time_str = f"{h:02}:{m:02}:{s:02}"
        else:
            # Show MM:SS otherwise
             time_str = f"{m:02}:{s:02}"

        # Format alarm trigger time
        alarm_trigger_time_str = ""
        if self.end_datetime:
             # Format as h:mm AP/PM
             alarm_trigger_time_str = self.end_datetime.toString("h:mm AP").replace("AM", "am").replace("PM", "pm")

        # Update the display label, respecting colon blinking (only in RUNNING state)
        if self.current_state == TimerState.RUNNING:
             if self.colon_visible:
                 self.timer_display_widget.update_time_display(time_str, alarm_trigger_time_str)
             else:
                 # Replace colons with spaces for blinking effect
                 # Only replace colons if they exist in the formatted time string
                 time_str_blink = time_str.replace(':', ' ') if ':' in time_str else time_str
                 self.timer_display_widget.update_time_display(time_str_blink, alarm_trigger_time_str)
        # else: # No need for else, PAUSED state handles its display in update_ui_state
        #      # In PAUSED state, colon is always visible
        #      self.timer_display_widget.update_time_display(time_str, alarm_trigger_time_str)


        # Calculate progress for the circular indicator
        if self.total_seconds_at_start > 0:
            # Progress goes from 1.0 (full) to 0.0 (empty)
            # Use precise remaining_seconds for progress calculation
            self.progress = self.remaining_seconds / self.total_seconds_at_start
        else:
            self.progress = 0.0

        # Trigger repaint for circle animation (also called by update_timer_animation)
        # Calling here ensures circle updates even if animation_timer isn't running (e.g., debugging)
        self.update()


    def blink_colon(self):
        """Toggles colon visibility for blinking effect."""
        # Only blink if timer is RUNNING
        if self.current_state == TimerState.RUNNING:
            self.colon_visible = not self.colon_visible
            # The update_timer_logic method will handle updating the display with/without colon
        # else: # If not running, ensure colon is visible
        #      if not self.colon_visible:
        #          self.colon_visible = True
        #          self.update_timer_logic() # Force update to show colon


    # --- Painting Logic ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the black background with rounded corners
        path = QPainterPath()
        rect = QRectF(self.rect())
        path.addRoundedRect(rect, self.corner_radius, self.corner_radius)
        painter.fillPath(path, QColor("black"))

        # --- Draw Circular Progress Indicator ---
        # Draw only if in RUNNING or PAUSED state and total time was set
        if self.current_state in [TimerState.RUNNING, TimerState.PAUSED] and self.total_seconds_at_start > 0:
            # The circle should be centered within the stacked widget
            if not self.stacked_widget:
                print("Warning: Stacked widget not found for drawing circle.")
                return

            try:
                # Calculate the bounding rectangle for the circle centered within the stacked widget
                stacked_widget_rect = self.stacked_widget.geometry()
                available_size = min(stacked_widget_rect.width(), stacked_widget_rect.height())

                # Calculate circle diameter relative to the available space, ensuring padding
                # Adjusted padding factor as needed for visual balance at min size
                padding_factor = 0.1 # 10% of available size for padding
                circle_diameter = available_size * (1.0 - padding_factor)
                # Ensure minimum diameter to prevent circle from disappearing or being too small
                # Adjusted minimum diameter based on visual testing
                min_circle_diameter = 150 # Increased minimum diameter
                circle_diameter = max(min_circle_diameter, circle_diameter)


                # Calculate the top-left corner of the circle rectangle
                # Center the circle within the stacked widget's geometry
                circle_x = stacked_widget_rect.center().x() - circle_diameter / 2
                circle_y = stacked_widget_rect.center().y() - circle_diameter / 2

                circle_rect = QRectF(circle_x, circle_y, circle_diameter, circle_diameter)

                # Adjust the rectangle inwards by half the line thickness for drawing
                line_thickness = 8 # Ensure this matches the pen width
                circle_rect.adjust(line_thickness / 2, line_thickness / 2, -line_thickness / 2, -line_thickness / 2)

                # Ensure circle_rect is valid and within reasonable bounds
                if circle_rect.width() <= 0 or circle_rect.height() <= 0 or circle_rect.width() > self.width() * 2:
                     print("Warning: Invalid circle rectangle dimensions.")
                     return

                # Set pen for drawing
                pen = QPen(QColor("#FF9500")) # Bright orange
                pen.setWidth(line_thickness)
                pen.setCapStyle(Qt.RoundCap) # Rounded ends

                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)

                # Draw the progress arc
                # Angle starts at 90 degrees (top) and goes counter-clockwise.
                # Full circle is 360 * 16 units for QPainter.
                # Remaining angle = progress * 360 degrees.
                # Starting from the top (90 degrees), we draw an arc of `progress * 360` degrees
                # in the *counter-clockwise* direction (positive angle) to show the remaining part.
                start_angle = 90 * 16 # Top of the circle
                # Sweep angle is proportional to REMAINING time, drawn counter-clockwise (positive)
                sweep_angle = int(self.progress * 360 * 16)

                painter.drawArc(circle_rect, start_angle, sweep_angle)


                # (Optional) Draw a faint grey circle behind to show the full circle track
                # pen.setColor(QColor(50, 50, 50, 100)) # Faint grey
                # painter.setPen(pen)
                # painter.drawEllipse(circle_rect)


            except Exception as e:
                 print(f"Error drawing circular progress indicator: {e}")

        # Child widgets (labels, buttons, picker) are painted automatically on top.


    # --- Resize Logic ---
    def resizeEvent(self, event):
        # Переопределяем resizeEvent для принудительного пропорционального масштабирования
        new_size = event.size()
        current_size = self.size()

        # Вычисляем желаемую ширину и высоту основной части окна, сохраняя соотношение сторон
        # Используем меньшее из изменений для определения нового размера основной части
        # Учитываем, что общая высота окна включает нижнюю панель и, возможно, расширяемую секцию
        current_main_height = current_size.height() - self.bottom_bar_frame.height() - (self.layout().contentsMargins().bottom() if self.layout() else 0)
        if self.expanded:
             current_main_height -= self.expanded_section_height # Вычитаем высоту расширяемой секции, если она видима

        # Рассчитываем scale_factor на основе текущих размеров основной части
        scale_factor_width = new_size.width() / self.initial_width
        scale_factor_height = current_main_height / self.initial_main_height # Используем текущую высоту основной части

        # Используем меньший scale_factor для сохранения пропорций
        scale_factor = min(scale_factor_width, scale_factor_height)
        scale_factor = max(0.5, scale_factor) # Предотвращаем слишком сильное уменьшение

        # Вычисляем целевые размеры основной части окна
        target_main_width = int(self.initial_width * scale_factor)
        target_main_height = int(self.initial_main_height * scale_factor)

        # Применяем минимальный размер к основной части
        min_main_width = int(self.minimumWidth() * (self.initial_width / self.initial_width)) # Минимальная ширина масштабируется по ширине
        min_main_height = int(self.minimumHeight() * (self.initial_main_height / self.initial_total_height)) # Минимальная высота основной части

        target_main_width = max(target_main_width, min_main_width)
        target_main_height = max(target_main_height, min_main_height)


        # Вычисляем целевую общую высоту окна
        target_total_height = target_main_height + self.bottom_bar_frame.height() + (self.layout().contentsMargins().bottom() if self.layout() else 0)
        if self.expanded:
             target_total_height += self.expanded_section_height # Добавляем высоту расширяемой секции, если она видима

        # Применяем минимальную общую высоту
        target_total_height = max(target_total_height, self.minimumHeight())


        # Проверяем, нужно ли изменить размер окна
        if target_main_width != current_size.width() or target_total_height != current_size.height():
             # Изменяем размер окна на вычисленный пропорциональный размер
             self.resize(target_main_width, target_total_height)
             # Важно: После resize() снова вызывается resizeEvent.
             # Чтобы избежать бесконечного цикла, нужно убедиться, что при следующем вызове
             # new_size будет равен target_size, и мы не попадем в эту ветку снова.
             # Это достигается тем, что self.resize() устанавливает фактический размер окна.


        # Теперь, когда размер окна установлен пропорционально, масштабируем элементы внутри
        # Используем актуальный scale_factor, рассчитанный на основе текущих размеров основной части
        actual_current_main_height = self.height() - self.bottom_bar_frame.height() - (self.layout().contentsMargins().bottom() if self.layout() else 0)
        if self.expanded:
             actual_current_main_height -= self.expanded_section_height

        scale_factor = min(self.width() / self.initial_width, actual_current_main_height / self.initial_main_height)
        scale_factor = max(0.5, scale_factor) # Предотвращаем слишком сильное уменьшение


        # Scale button font and size
        if self.start_pause_button and self.cancel_button:
             try:
                 new_button_font_size = int(self.initial_button_font_size * scale_factor)
                 new_button_font_size = max(10, new_button_font_size) # Min size 10
                 font = self.start_pause_button.font()
                 font.setPointSize(new_button_font_size)
                 self.start_pause_button.setFont(font)
                 self.cancel_button.setFont(font)

                 # Scale button size based on scale factor
                 new_button_size = QSize(
                     int(self.initial_button_size.width() * scale_factor),
                     int(self.initial_button_size.height() * scale_factor)
                 )
                 new_button_size = QSize(max(40, new_button_size.width()), max(40, new_button_size.height())) # Min size 40x40

                 self.start_pause_button.setFixedSize(new_button_size)
                 self.cancel_button.setFixedSize(new_button_size)

                 # Adjust spacing between buttons based on scale factor
                 # Keep a minimum spacing
                 new_button_spacing = int(70 * scale_factor) # Initial spacing was 70
                 new_button_spacing = max(30, new_button_spacing) # Minimum spacing 30
                 self.buttons_layout.setSpacing(new_button_spacing)


             except AttributeError: pass

        # Scale time display font
        if self.timer_display_widget: # Check if widget exists
             try:
                 # Scale font size based on the same scale factor
                 # Adjust multiplier (1.5) as needed for visual balance relative to circle size
                 new_time_font_size = int(self.initial_display_time_font_size * scale_factor * 1.5)
                 # Уменьшаем минимальный размер шрифта цифр (был 30) и корректируем базовый множитель
                 new_time_font_size = max(30, new_time_font_size) # Ensure a reasonable minimum size
                 self.timer_display_widget.set_time_font_size(new_time_font_size) # <--- Здесь устанавливается новый размер
             except (AttributeError, ZeroDivisionError) as e:
                 print(f"Error scaling timer font size: {e}")
                 pass # Catch if set_time_font_size doesn't exist or calculation is invalid

          # Scale alarm info font
        if self.timer_display_widget: # Check if widget exists
             try:
                 new_alarm_info_font_size = int(self.initial_alarm_info_font_size * scale_factor)
                 new_alarm_info_font_size = max(8, new_alarm_info_font_size) # Min size 8
                 self.timer_display_widget.set_alarm_info_font_size(new_alarm_info_font_size)
             except AttributeError: pass # Catch if set_alarm_info_font_size doesn't exist or widget is None


        # Вызываем paintEvent для перерисовки фона и круга с учетом нового размера
        self.update()


    # --- Window Dragging Logic (now handled by CustomTitleBar) ---
    # Removing these methods as dragging is handled by the title bar
    # def mousePressEvent(self, event): pass
    # def mouseMoveEvent(self, event): pass
    # def mouseReleaseEvent(self, event): pass


    # --- toggle_expandable_section (keep as is) ---
    def toggle_expandable_section(self):
        current_width = self.width()
        current_height = self.height()
        if self.expanded:
            self.expanded = False
            self.toggle_button.setText("^")
            self.toggle_button.setChecked(False)
            self.expandable_widget.hide()
            # При скрытии секции, уменьшаем общую высоту окна на высоту секции
            new_height = current_height - self.expanded_section_height
            self.resize(current_width, new_height)
            # Корректируем минимальную высоту окна
            min_h = self.minimumHeight() - self.expanded_section_height
            self.setMinimumHeight(min_h) # Устанавливаем новый минимальный размер

        else:
            self.expanded = True
            self.toggle_button.setText("v")
            self.toggle_button.setChecked(True)
            # При показе секции, увеличиваем общую высоту окна на высоту секции
            new_height = current_height + self.expanded_section_height
            self.resize(current_width, new_height)
            # Корректируем минимальную высоту окна
            new_min_height = self.minimumHeight() + self.expanded_section_height
            self.setMinimumHeight(new_min_height) # Устанавливаем новый минимальный размер

            self.expandable_widget.show()

        self.layout().activate()
        self.update()


    # --- Alarm Sound Logic (keep as is) ---
    def play_alarm(self):
        if self.alarm_playing: return
        try:
            if not pygame.mixer.get_init():
                 print("Initializing pygame mixer...")
                 try: pygame.mixer.pre_init(44100, -16, 2, 2048); pygame.mixer.init()
                 except pygame.error as init_err: print(f"Failed to initialize pygame mixer: {init_err}"); return

            # Determine the directory of the script or the executable
            if getattr(sys, 'frozen', False):
                 # If running as a bundled executable (e.g., PyInstaller)
                 script_dir = sys._MEIPASS
            else:
                 # If running as a normal script
                 script_dir = os.path.dirname(os.path.abspath(__file__))

            sound_path = os.path.join(script_dir, "alarm.wav") # <--- Font file relative to script/exe

            if not os.path.exists(sound_path):
                 # Fallback to checking current working directory
                 sound_path_cwd = os.path.join(os.getcwd(), "alarm.wav")
                 if os.path.exists(sound_path_cwd):
                      sound_path = sound_path_cwd
                 else:
                      print(f"Error: alarm.wav not found in '{script_dir}' or '{os.getcwd()}'")
                      self.alarm_playing = False
                      return

            print(f"Loading sound: {sound_path}")
            pygame.mixer.music.load(sound_path)
            print("Playing sound...")
            pygame.mixer.music.play(loops=-1) # Play indefinitely until stopped
            self.alarm_playing = True
            # No need for QTimer.singleShot, alarm plays until stopped by Cancel
            # QTimer.singleShot(2000, self.reset_alarm_flag) # Removed this line
        except pygame.error as e: print(f"Pygame error playing sound: {e}"); self.alarm_playing = False
        except Exception as e: print(f"Unexpected error playing sound: {e}"); self.alarm_playing = False

    # This function might not be needed anymore if alarm_playing is reset in stop_alarm_sound
    # def reset_alarm_flag(self):
    #     """Resets the alarm playing flag."""
    #     self.alarm_playing = False

    # --- Transparency and Click-through Logic ---
    def toggle_transparent_mode(self, checked):
        """Тогглинг прозрачности и кликабельности рабочей части."""
        self.transparent_mode_enabled = checked
        if self.transparent_mode_enabled:
            # Включаем режим прозрачности и делаем рабочую часть некликабельной
            self.content_transparent = True
            # Окно становится прозрачным при наведении мышью (обрабатывается в eventFilter)
            # Устанавливаем атрибуты для игнорирования событий мыши на виджетах
            self.stacked_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.cancel_button.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.start_pause_button.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.expandable_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.bottom_bar_frame.setAttribute(Qt.WA_TransparentForMouseEvents)
        else:
            # Выключаем прозрачность и восстанавливаем кликабельность
            self.content_transparent = False
            self.setWindowOpacity(1.0)  # Возвращаем нормальную непрозрачность
            # Возвращаем нормальную кликабельность
            self.stacked_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.cancel_button.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.start_pause_button.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.expandable_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.bottom_bar_frame.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.update()  # Перерисовываем окно для применения изменений


    def eventFilter(self, obj, event):
        """Фильтрация событий мыши для работы с прозрачностью."""
        # Handle mouse entry/exit for opacity change on the main window
        if obj == self:
            if self.transparent_mode_enabled:
                if event.type() == QEvent.Enter:
                    # Когда курсор входит в окно, включаем прозрачность
                    self.setWindowOpacity(0.1)  # Очень прозрачное окно
                    return False # Allow event propagation

                elif event.type() == QEvent.Leave:
                    # Когда курсор выходит, восстанавливаем обычное состояние
                    self.setWindowOpacity(1.0)  # Обычная непрозрачность
                    return False # Allow event propagation

                # Handle mouse interaction events for click-through
                # Intercept relevant mouse events on the main window object
                if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick, QEvent.MouseMove]:
                     # Determine which widget is at the global mouse position
                     widget_under_mouse = QApplication.widgetAt(event.globalPos())

                     # Check if the widget under the mouse is the title bar or one of its children
                     is_in_title_bar_area = False
                     if widget_under_mouse:
                          # Traverse up the parent hierarchy to see if the title bar is an ancestor
                          current_widget = widget_under_mouse
                          while current_widget is not None:
                               if current_widget == self.title_bar:
                                   is_in_title_bar_area = True
                                   break
                               current_widget = current_widget.parent()

                     if is_in_title_bar_area:
                          # Mouse is over the title bar or its children, allow event processing
                          return False # Let the event propagate normally
                     else:
                          # Mouse is over the main timer interface area, consume the event
                          # This makes the area "click-through"
                          event.ignore() # Ignore the event
                          return True # Consume the event


        # For all other objects or events, pass them through
        return super().eventFilter(obj, event)

    # ------------------------------------------


# --- Application Entry Point ---
if __name__ == "__main__":
    # Initialize Pygame
    try:
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.init()
        print("Pygame initialized.")
    except Exception as e:
        print(f"Error initializing Pygame: {e}")

    app = QApplication(sys.argv)

    # --- Set SF Pro Display font ---
    # IMPORTANT: Replace with the actual path to your SF Pro Display font file.
    # The font file (e.g., SF-Pro-Display-Regular.otf) must be accessible.
    # Place the file next to your script or provide a full path.
    # You might need multiple font files for different weights (Regular, Light)
    # For simplicity, we load one and rely on setPointSize.

    # Determine the directory of the script or the executable for font loading
    if getattr(sys, 'frozen', False):
        # If running as a bundled executable (e.g., PyInstaller)
        script_dir = sys._MEIPASS
    else:
        # If running as a normal script
        script_dir = os.path.dirname(os.path.abspath(__file__))

    font_path = os.path.join(script_dir, "SF-Pro-Display-Regular.otf") # <--- Font file relative to script/exe

    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id != -1:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            # Set SF Pro Display as the default application font
            default_font = QFont(families[0])
            # Set a base size, widget-specific sizes will be applied later
            default_font.setPointSize(9)
            app.setFont(default_font)
            print(f"Font '{families[0]}' loaded from '{font_path}' and set.")
        else:
            print(f"Error: Could not get font families from file '{font_path}'.")
            print("Using system fallback font.")
            # Fallback to a similar system font
            default_font = QFont('Segoe UI', 9) # Windows
            if sys.platform == 'darwin':
                 default_font = QFont('Helvetica Neue', 9) # macOS
            elif sys.platform.startswith('linux'):
                 default_font = QFont('Roboto', 9) # Linux
            app.setFont(default_font)
    else:
        print(f"Note: Font file '{font_path}' not found or could not be loaded.")
        # Fallback to checking current working directory
        font_path_cwd = os.path.join(os.getcwd(), "SF-Pro-Display-Regular.otf")
        font_id_cwd = QFontDatabase.addApplicationFont(font_path_cwd)
        if font_id_cwd != -1:
            families_cwd = QFontDatabase.applicationFontFamilies(font_id_cwd)
            if families_cwd:
                default_font = QFont(families_cwd[0])
                default_font.setPointSize(9)
                app.setFont(default_font)
                print(f"Font '{families_cwd[0]}' loaded from '{font_path_cwd}' and set.")
            else: # Should not happen if font_id_cwd != -1
                 print("Using system fallback font after CWD check failed.")
                 default_font = QFont('Segoe UI', 9); app.setFont(default_font) # Fallback
            app.setFont(default_font) # Ensure font is set
        else:
            print("Using system fallback font.")
            # Fallback to a similar system font
            default_font = QFont('Segoe UI', 9) # Windows
            if sys.platform == 'darwin':
                 default_font = QFont('Helvetica Neue', 9) # macOS
            elif sys.platform.startswith('linux'):
                 default_font = QFont('Roboto', 9) # Linux
            app.setFont(default_font)


    timer_app = TimerApp() # Use the main app class
    timer_app.show()
    exit_code = app.exec_()

    pygame.quit()
    print("Pygame finalized.")
    sys.exit(exit_code)

