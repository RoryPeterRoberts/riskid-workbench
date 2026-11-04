# A single-file build of the workbench for people who cannot install Python (SPEC.md section 9).
#
# Build, from the repository root, in an environment where the workbench and PyInstaller are
# installed (`pip install . pyinstaller`):
#     pyinstaller packaging/riskid.spec
# The result is dist/riskid (dist/riskid.exe on Windows), which takes the same commands as
# `riskid`: `riskid init my.riskid`, then `riskid serve my.riskid`. A .riskid file moves freely
# between this build and a pipx install.
#
# WeasyPrint draws PDFs through Pango, which it loads from the system at run time: present on
# most Linux desktops; on Windows and macOS it has to be installed or bundled (docs/LATER.md).

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
for package in ("riskid", "weasyprint", "docx"):    # data packs, templates, CSS, the docx template
    datas += collect_data_files(package)
# uvicorn and the workbench import some of their modules by name at run time.
hiddenimports = collect_submodules("uvicorn") + collect_submodules("riskid")

a = Analysis(["launcher.py"], datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="riskid", console=True)
