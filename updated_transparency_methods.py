# --- Transparency and Click-through Logic ---
def toggle_transparent_mode(self, checked):
    """Toggles transparency mode based on the switch state."""
    self.transparent_mode_enabled = checked
    
    # When toggle is turned on, we don't immediately make the window transparent
    # It will become transparent only when the mouse enters the window
    # and will become opaque when the mouse leaves
    
    if self.transparent_mode_enabled:
        # Make all widgets except title_bar non-clickable (transparent for mouse events)
        self.stacked_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.cancel_button.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.start_pause_button.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.expandable_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.bottom_bar_frame.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        # Important: Do NOT set WA_TransparentForMouseEvents for the title_bar
        # so it remains clickable for dragging and buttons
        
        # Set window flag to allow mouse events to pass through
        self.setWindowFlag(Qt.WindowTransparentForInput, True)
        
        # Hide and show to apply window flag changes
        self.hide()
        self.show()
        
        # Start with normal opacity - will become transparent on mouse enter
        self.setWindowOpacity(1.0)
    else:
        # When toggle is turned off, restore normal behavior
        self.stacked_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.cancel_button.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.start_pause_button.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.expandable_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.bottom_bar_frame.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # Disable window transparency for input
        self.setWindowFlag(Qt.WindowTransparentForInput, False)
        
        # Ensure window is fully opaque
        self.setWindowOpacity(1.0)
        
        # Hide and show to apply window flag changes
        self.hide()
        self.show()
    
    # Repaint to apply visual changes
    self.update()

def eventFilter(self, obj, event):
    """Filters events for transparency and click-through behavior."""
    if obj == self:
        if self.transparent_mode_enabled:
            if event.type() == QEvent.Enter:
                # When mouse enters the window and transparency is enabled,
                # make the window transparent
                self.setWindowOpacity(0.3)  # Adjust transparency level as needed
                return False  # Allow event to propagate
                
            elif event.type() == QEvent.Leave:
                # When mouse leaves the window and transparency is enabled,
                # make the window opaque again
                self.setWindowOpacity(1.0)
                return False  # Allow event to propagate
                
            # Handle mouse events for click-through behavior
            if event.type() in [QEvent.MouseButtonPress, QEvent.MouseButtonRelease, 
                               QEvent.MouseButtonDblClick, QEvent.MouseMove]:
                # Get mouse position in global coordinates
                global_pos = event.globalPos()
                
                # Check if cursor is over the title bar or its elements
                widget_under_mouse = QApplication.widgetAt(global_pos)
                
                is_in_title_bar_area = False
                
                # Check if the widget under cursor is part of the title bar
                if widget_under_mouse:
                    current_widget = widget_under_mouse
                    while current_widget is not None:
                        # Check if current widget is the title bar or one of its interactive elements
                        if (current_widget == self.title_bar or 
                            hasattr(self, 'title_bar') and current_widget == self.title_bar.close_button or 
                            hasattr(self, 'title_bar') and current_widget == self.title_bar.minimize_button or 
                            hasattr(self, 'title_bar') and current_widget == self.title_bar.transparent_toggle or 
                            hasattr(self, 'title_bar') and current_widget == self.title_bar.title_label):
                            is_in_title_bar_area = True
                            break
                        # Move up to parent
                        current_widget = current_widget.parent()
                
                # Handle event based on cursor location
                if is_in_title_bar_area:
                    # If cursor is over title bar or its elements, handle click normally
                    # Event will be passed to the appropriate widget (title_bar or buttons)
                    return False  # Allow event to propagate
                else:
                    # If cursor is on the content area, pass click through
                    # Thanks to WindowTransparentForInput flag, event will pass through to OS
                    # We just consume the event here so it's not processed by the main window
                    return True  # Consume event
    
    # For all other objects or events, let them propagate
    return super().eventFilter(obj, event)
