# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['customtkinter', 'matplotlib', 'PIL', 'plyer', 'pystray', 'bcrypt', 'openpyxl', 'reportlab', 'database', 'version', 'kur',
                   'db', 'db.borc', 'db.kategori', 'db.kullanici', 'db.planlama',
                   'db.tasarruf', 'db.tekrarlayan', 'db._temel',
                   'ui', 'ui.ayarlar', 'ui.bakiye_widget', 'ui.butce', 'ui.dashboard', 'ui.gelir', 'ui.gider', 'ui.giris', 'ui.global_arama', 'ui.grafikler', 'ui.hakkinda', 'ui.islem_formu', 'ui.money', 'ui.planlama', 'ui.tema', 'ui.utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FINEding',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app_icon.ico'],
)
