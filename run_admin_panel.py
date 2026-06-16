import os
import shutil
import subprocess
import sys

from backend.lr_admin_pannel.main import main


def run_with_display():
    if os.environ.get('DISPLAY'):
        main()
        return

    xvfb_run = shutil.which('xvfb-run')
    if xvfb_run:
        env = os.environ.copy()
        env['LR_ADMIN_XVFB'] = '1'
        raise SystemExit(subprocess.call([xvfb_run, '-a', sys.executable, '-m', 'backend.lr_admin_pannel.main'], env=env))

    raise SystemExit(
        'LR Admin Panel is a Tkinter desktop app, but no display is available.\n'
        'Install Xvfb, then run this command again:\n'
        '  sudo apt-get update && sudo apt-get install -y xvfb\n'
        'Or run it from a desktop/VNC session with DISPLAY set.'
    )


if __name__ == '__main__':
    run_with_display()
