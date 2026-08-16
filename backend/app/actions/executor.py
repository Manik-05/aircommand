"""
Executes an Action (shared/schemas.py::Action) on the host machine.
MVP only implements "keyboard". mouse/browser/app are Phase 2.
"""
from pynput.keyboard import Controller, Key

_keyboard = Controller()

_KEY_MAP = {
    "ctrl": Key.ctrl,
    "alt": Key.alt,
    "shift": Key.shift,
    "cmd": Key.cmd,
    "tab": Key.tab,
    "enter": Key.enter,
    "esc": Key.esc,
    "space": Key.space,
}


def execute(action: dict) -> None:
    if action["type"] == "keyboard":
        keys = [_KEY_MAP.get(k, k) for k in action["payload"]["keys"]]
        for k in keys:
            _keyboard.press(k)
        for k in reversed(keys):
            _keyboard.release(k)
    else:
        raise NotImplementedError(f"action type {action['type']} not implemented yet")
