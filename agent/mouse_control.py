try:
    import pyautogui
except ImportError:
    pyautogui = None


class MouseControl:
    def __init__(self):
        if pyautogui:
            pyautogui.FAILSAFE = False

    def handle_event(self, event):
        if pyautogui is None:
            return {'success': False, 'error': 'pyautogui is not installed'}

        event = event or {}
        action = event.get('action')
        x = event.get('x')
        y = event.get('y')
        button = event.get('button', 'left')
        scroll_y = event.get('scroll_y', event.get('dy', 0))

        if action == 'move':
            pyautogui.moveTo(int(x), int(y))
        elif action == 'click':
            pyautogui.click(int(x), int(y), button=button)
        elif action == 'down':
            if x is not None and y is not None:
                pyautogui.moveTo(int(x), int(y))
            pyautogui.mouseDown(button=button)
        elif action == 'up':
            if x is not None and y is not None:
                pyautogui.moveTo(int(x), int(y))
            pyautogui.mouseUp(button=button)
        elif action == 'double_click':
            pyautogui.doubleClick(int(x), int(y), button=button)
        elif action == 'right_click':
            pyautogui.click(int(x), int(y), button='right')
        elif action == 'scroll':
            pyautogui.scroll(int(scroll_y))
        elif action == 'drag':
            pyautogui.dragTo(int(x), int(y), duration=float(event.get('duration', 0.05)), button=button)
        else:
            return {'success': False, 'error': f'Unknown mouse action: {action}'}

        return {'success': True}
