def toggle_transparent_mode(self, checked):
    """Тогглинг прозрачности и кликабельности рабочей части."""
    self.transparent_mode_enabled = checked
    if self.transparent_mode_enabled:
        # Включаем режим прозрачности и делаем рабочую часть некликабельной
        self.content_transparent = True
        self.setWindowOpacity(0.1)  # Сделать окно прозрачным
        
        # Делаем все виджеты некликабельными (прозрачными для мыши)
        self.stacked_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.cancel_button.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.start_pause_button.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.expandable_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.bottom_bar_frame.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        # Делаем основное окно прозрачным для мыши, но НЕ делаем title_bar прозрачным
        # Важно: НЕ устанавливаем WA_TransparentForMouseEvents для self (всего окна)
        # и НЕ устанавливаем для title_bar, чтобы он оставался кликабельным
        
        # Устанавливаем флаг, чтобы окно пропускало клики мыши, кроме заголовка
        self.setWindowFlag(Qt.WindowTransparentForInput, True)
        
        # Обновляем окно, чтобы применить изменения флагов
        self.hide()
        self.show()
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
        
        # Отключаем флаг прозрачности для ввода
        self.setWindowFlag(Qt.WindowTransparentForInput, False)
        
        # Обновляем окно, чтобы применить изменения флагов
        self.hide()
        self.show()
    
    self.update()  # Перерисовываем окно для применения изменений

def eventFilter(self, obj, event):
    """Фильтрация событий мыши для работы с прозрачностью."""
    if obj == self and self.transparent_mode_enabled:
        if event.type() == QEvent.Enter:
            # Когда курсор входит в окно, включаем прозрачность
            self.setWindowOpacity(0.1)  # Очень прозрачное окно
            return False
        elif event.type() == QEvent.Leave:
            # Когда курсор выходит, восстанавливаем обычное состояние
            self.setWindowOpacity(1.0)  # Обычная непрозрачность
            return False
        
        # В прозрачном режиме проверяем, находится ли курсор над заголовком
        if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                            QEvent.MouseButtonDblClick, QEvent.MouseMove]:
            # Получаем позицию мыши в глобальных координатах
            global_pos = event.globalPos()
            
            # Проверяем, находится ли курсор над заголовком окна
            widget_under_mouse = QApplication.widgetAt(global_pos)
            
            # Проверяем, является ли виджет под курсором частью заголовка
            is_in_title_bar_area = False
            
            if widget_under_mouse:
                # Проверяем, является ли виджет или его родители частью заголовка
                current_widget = widget_under_mouse
                while current_widget is not None:
                    # Проверяем, является ли текущий виджет заголовком или его компонентом
                    if (hasattr(self, 'title_bar') and current_widget == self.title_bar or
                        hasattr(self, 'close_button') and current_widget == self.close_button or
                        hasattr(self, 'minimize_button') and current_widget == self.minimize_button or
                        hasattr(self, 'app_title_label') and current_widget == self.app_title_label or
                        hasattr(self, 'power_button') and current_widget == self.power_button):
                        is_in_title_bar_area = True
                        break
                    current_widget = current_widget.parent()
            
            # Обрабатываем событие в зависимости от того, где находится курсор
            if is_in_title_bar_area:
                # Если курсор над заголовком, обрабатываем клик как обычно
                return False
            else:
                # Если курсор на рабочей области, пропускаем клик (сквозной)
                return True
    
    # Для всех остальных случаев используем стандартную обработку
    return super().eventFilter(obj, event)

# Добавляем метод для установки обработчика событий при инициализации
def setup_event_handling(self):
    """Настройка обработки событий для прозрачного режима."""
    # Устанавливаем фильтр событий для окна
    self.installEventFilter(self)
    
    # Убедимся, что title_bar определен
    if not hasattr(self, 'title_bar'):
        # Если title_bar не определен, создаем его
        self.title_bar = QWidget(self)
        self.title_bar.setObjectName('title_bar')
        
        # Создаем компоненты заголовка, если они еще не созданы
        if not hasattr(self, 'close_button'):
            self.close_button = QPushButton("×", self.title_bar)
            self.close_button.clicked.connect(self.close)
        
        if not hasattr(self, 'minimize_button'):
            self.minimize_button = QPushButton("−", self.title_bar)
            self.minimize_button.clicked.connect(self.showMinimized)
        
        if not hasattr(self, 'app_title_label'):
            self.app_title_label = QLabel("Приложение", self.title_bar)
        
        if not hasattr(self, 'power_button'):
            self.power_button = QPushButton("⏻", self.title_bar)
            # Подключаем сигнал к соответствующему слоту
            # self.power_button.clicked.connect(self.power_action)
        
        # Размещаем компоненты в заголовке
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.addWidget(self.app_title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(self.close_button)
        title_layout.addWidget(self.power_button)
        
        # Добавляем заголовок в основной макет
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.title_bar)
        # Здесь должны быть добавлены остальные виджеты в main_layout
