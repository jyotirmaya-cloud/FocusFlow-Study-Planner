@echo off
echo ==== FocusFlow: building the Windows app ====
echo.
echo [1/2] Installing build tools...
python -m pip install --upgrade pyinstaller customtkinter
echo.
echo [2/2] Building FocusFlow.exe (this takes a minute or two)...
python -m PyInstaller --noconfirm --clean --noconsole --onefile --name FocusFlow --icon icon.ico --add-data "icon.ico;." --collect-all customtkinter main.py
echo.
echo ==== Done! Your app is here: dist\FocusFlow.exe ====
pause
