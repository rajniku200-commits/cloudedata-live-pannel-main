try:
    import pyautogui
except ImportError:
    pyautogui = None


class KeyboardControl:
    def __init__(self):
        if pyautogui:
            pyautogui.FAILSAFE = False

    def handle_event(self, event):
        if pyautogui is None:
            return {'success': False, 'error': 'pyautogui is not installed'}

        event = event or {}
        action = event.get('action')
        key = event.get('key')
        text = event.get('text')
        keys = event.get('keys') or []

        if action == 'press':
            pyautogui.press(key)
        elif action == 'down':
            pyautogui.keyDown(key)
        elif action == 'up':
            pyautogui.keyUp(key)
        elif action == 'hotkey':
            pyautogui.hotkey(*keys)
        elif action == 'write':
            pyautogui.write(text or '', interval=float(event.get('interval', 0)))
        else:
            return {'success': False, 'error': f'Unknown keyboard action: {action}'}

        return {'success': True}
