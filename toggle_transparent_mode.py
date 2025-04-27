def toggle_transparent_mode(self, checked):
    """Тогглинг прозрачности и кликабельности рабочей части."""
    self.transparent_mode_enabled = checked
    if self.transparent_mode_enabled:
        # Включаем режим прозрачности и делаем рабочую часть некликабельной
        self.content_transparent = True
        self.setWindowOpacity(0.1)  # Сделать окно прозрачным
        # Скрываем рабочие виджеты, чтобы они не принимали клики
        self.stacked_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.cancel_button.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.start_pause_button.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.expandable_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.bottom_bar_frame.setAttribute(Qt.WA_TransparentForMouseEvents)
        # Устанавливаем флаг, чтобы окно пропускало клики мыши
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        # Устанавливаем флаг, чтобы окно не блокировало события мыши
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
        # Отключаем прозрачность для кликов мыши
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
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
        
        # В прозрачном режиме пропускаем все события мыши, кроме событий в заголовке
        if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                            QEvent.MouseButtonDblClick, QEvent.MouseMove]:
            # Проверка, если курсор находится над заголовком окна
            widget_under_mouse = QApplication.widgetAt(event.globalPos())
            is_in_title_bar_area = False
            
            # Проверяем, не находится ли курсор над заголовком
            if widget_under_mouse:
                current_widget = widget_under_mouse
                while current_widget is not None:
                    if current_widget == self.title_bar:
                        is_in_title_bar_area = True
                        break
                    current_widget = current_widget.parent()
            
            if is_in_title_bar_area:
                # Если курсор над заголовком, обрабатываем клик как обычно
                self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
                return False
            else:
                # Если курсор на рабочей области, пропускаем клик (сквозной)
                self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                return True
    
    return super().eventFilter(obj, event)

# Добавляем метод для установки обработчика событий при инициализации
def setup_event_handling(self):
    """Настройка обработки событий для прозрачного режима."""
    # Устанавливаем фильтр событий для окна
    self.installEventFilter(self)
    
    # Убедимся, что title_bar определен
    if not hasattr(self, 'title_bar'):
        # Если title_bar не определен, создаем его или используем другой виджет
        # Это зависит от вашей реализации интерфейса
        # Например:
        # self.title_bar = self.findChild(QWidget, 'title_bar')
        # или
        # self.title_bar = QWidget(self)
        # self.title_bar.setObjectName('title_bar')
        # layout = QVBoxLayout(self)
        # layout.addWidget(self.title_bar)
        pass  # Удалите эту строку и раскомментируйте нужный код выше
