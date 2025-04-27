# Window Transparency Feature Implementation

This repository contains the implementation of a window transparency feature for a PyQt5 timer application. The feature allows the window to become transparent when the mouse cursor is over it, but only when the transparency toggle switch is enabled.

## Feature Requirements

1. The window should be transparent only when:
   - The toggle switch is ON
   - The mouse cursor is over the window
2. When transparent, the interface window should not be clickable (except for the title bar)
3. When the mouse cursor is moved away while the toggle is ON, the window should become clear and non-transparent

## Implementation Details

The implementation consists of two main methods that need to be added to the `TimerApp` class:

1. `toggle_transparent_mode(self, checked)`: This method is called when the toggle switch is clicked. It sets up the transparency behavior based on the toggle state.

2. `eventFilter(self, obj, event)`: This method handles mouse events to control transparency and click-through behavior.

## How to Implement

1. Replace the existing `toggle_transparent_mode` method in your `TimerApp` class with the one provided in `updated_transparency_methods.py`.

2. Replace the existing `eventFilter` method in your `TimerApp` class with the one provided in `updated_transparency_methods.py`.

3. Make sure the `TimerApp` class has the `installEventFilter(self)` call in its `__init__` method to enable event filtering.

## Key Features of the Implementation

- The window becomes transparent (30% opacity) when the mouse enters it and the toggle is ON
- The window becomes fully opaque when the mouse leaves it
- The title bar remains clickable for dragging and button interactions
- The rest of the window becomes click-through when transparent
- The transparency is toggled on/off using the iOS-style toggle switch in the title bar

## Notes

- You can adjust the transparency level by changing the value in `self.setWindowOpacity(0.3)` in the `eventFilter` method
- The implementation uses Qt's `WA_TransparentForMouseEvents` attribute to make widgets non-clickable
- The implementation uses Qt's `WindowTransparentForInput` flag to allow mouse events to pass through the window
