"""PyInstaller hook for ast-grep-py (Rust native extension).

ast_grep_py ships a platform-specific .so/.pyd binary that PyInstaller won't
discover through static import analysis.  This hook collects the binary and
any data files so they are bundled into af.exe.
"""
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

binaries = collect_dynamic_libs("ast_grep_py")
datas = collect_data_files("ast_grep_py")
hiddenimports = ["ast_grep_py"]
