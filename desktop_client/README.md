# LR Remote Access Desktop Client

This is the small desktop launcher for users. It shows a login screen, loads assigned apps from the LR server, and opens the selected remote app session.

Run during development:

```bash
python desktop_client/lr_remote_access_client.py
```

Build a Windows `.exe` on a Windows machine:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "LR Remote Access" desktop_client/lr_remote_access_client.py
```

Set the default server URL before building if needed:

```powershell
$env:LR_SERVER_URL="https://your-domain.com"
pyinstaller --onefile --windowed --name "LR Remote Access" desktop_client/lr_remote_access_client.py
```
