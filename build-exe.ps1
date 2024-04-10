py -3.9 -m venv .venv-spectroscopy
.venv-spectroscopy\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pyinstaller
pip install -r .\requirements.txt
pyinstaller --noconsole --onefile --icon .\assets\spectroscopy-logo.ico --add-data "assets/*:assets"  .\spectroscopy.py
deactivate