rmdir /Q /S build
rmdir /Q /S dist
rem Cannot bundle with ffmpeg due to license issues, this line is for future use only when I can build ffmpeg myself with x265 and switch to AV1 or similar
rem pyinstaller --add-data "data\icon.ico;data" --add-data "ffmpeg.exe;data" --add-data "ffprobe.exe;data" --paths "C:\Program Files (x86)\Windows Kits\10\Redist\10.0.17763.0\ucrt\DLLs\x86" --paths "venv\Lib\site-packages\shiboken2" --noconsole flix\gui.py  --icon data\icon.ico --name flix-bundle --clean --onefile
pyinstaller --add-data "data\icon.ico;data" --paths "C:\Program Files (x86)\Windows Kits\10\Redist\10.0.17763.0\ucrt\DLLs\x86" --paths "venv36\Lib\site-packages\shiboken2" --noconsole flix\gui.py  --icon data\icon.ico --name FastFlix --clean --onefile
