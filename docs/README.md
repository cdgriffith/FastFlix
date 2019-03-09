## Staying legal

Licencing is a pain, but it keeps everyone compliant and out of trouble. I try to make life easy for everyone 
by releasing my own software as MIT licences, however there are several caveats that must be observed if you
are to use or further copy this software.

### Dynamically linked libraries

Thankfully the wonderful creators of ffmpeg and PySide2 want their work shared and have provided use of their
software under the LGPL. The "catch" is that it has to overrideable so you can select your own version or
alternative instead.

#### Changing ffmpeg and ffprobe

Provide environment variables `FFMPEG` and `FFPROBE` with full paths to their respective 
executables prior to startup of the executable. It is also possible to select the directory they are 
located in via the GUI itself. 

```
set FFMPEG=C:\ffmpeg.exe
set FFPROBE=C:\ffprobe.exe
FastFlix.exe
```

#### Changing PySide2 (and shiboken2)

Similar to ffmpeg, PySide2 can be swapped out via environment variables. They can NOT later be swapped
out via the GUI itself, so to change it must be done via env vars. 
__
```
set PYSIDE2=venv\Lib\site-packages\PySide2\__init__.py
set SHIBOKEN2=venv\Lib\site-packages\shiboken2\__init__.py
FastFlix.exe
```

#### Changing SVT-AV1

You're not going to believe this, but you also can change SVT-AV1 encoder via env vars! 

```
set SVT-AV1=C:\SvtAv1EncApp.exe
FastFlix.exe
```

