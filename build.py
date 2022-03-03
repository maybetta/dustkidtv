import PyInstaller.__main__
import sys

if sys.platform=='win32':
    PyInstaller.__main__.run([
        'main.py',
        '--onefile',
        # '--add-data=dustkidtv/assets;dustkidtv/assets',
        # '--add-data=dflevels;dflevels',
        # '--add-data=dfreplays;dfreplays',
        # '--add-data=config.json;config.json',
    ])
else:
    PyInstaller.__main__.run([
        'main.py',
        '--onefile',
        # '--add-data=dustkidtv/assets:dustkidtv/assets',
        # '--add-data=dflevels:dflevels',
        # '--add-data=dfreplays:dfreplays',
        # '--add-data=config.json:config.json',
    ])
