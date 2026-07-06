# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — single source of truth for binary builds.
# Used by `make build` locally and by `.github/workflows/release.yml` in CI.
# Keep the EXCLUDES list in sync with the CLI's actual runtime needs.

from PyInstaller.utils.hooks import collect_data_files

# Everything the CLI does NOT need at runtime but gets pulled in transitively
# via agentrun-inner-test[core]. Excluding these keeps the binary small.
EXCLUDES = [
    'litellm',
    'tablestore',
    'agentrun_mem0ai',
    'agentrun_mem0',
    'alibabacloud_bailian20231229',
    'alibabacloud_gpdb20160503',
    'tiktoken',
    'tokenizers',
    'numpy',
    'grpcio',
    'torch',
    'tensorflow',
    'transformers',
    'PIL',
    'matplotlib',
    'scipy',
    'sklearn',
    'pandas',
    'pytz',
    'pygments',
    'sqlalchemy',
    'rich',
    'markdown_it',
    'mysql',
    'MySQLdb',
    'posthog',
    'jinja2',
    'qdrant_client',
    'huggingface_hub',
    'hf_xet',
    'fsspec',
    'h2',
    'regex',
    'future',
    'google',
]

datas = []
datas += collect_data_files('certifi')

a = Analysis(
    ['src/agentrun_cli/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/agentrun_cli/_utils/pyinstaller_certifi_hook.py'],
    excludes=EXCLUDES,
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
    name='agentrun',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
