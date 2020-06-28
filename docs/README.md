## Staying legal

Licencing is a pain, but it keeps everyone compliant and out of trouble. I try to make life easy for everyone
by releasing my own software as MIT licences, however there are several caveats that must be observed if you
are to use or further copy this software.

### Dynamically linked libraries

Thankfully the wonderful creators of PySide2 want their work shared and have provided use of their
software under the LGPL. The "catch" is that it has to overrideable so you can select your own version or
alternative instead.

#### Changing PySide2 (and shiboken2)

Similar to ffmpeg, PySide2 can be swapped out via environment variables. They can NOT later be swapped
out via the GUI itself, so to change it must be done via env vars.
__
```
set PYSIDE2=venv\Lib\site-packages\PySide2\__init__.py
set SHIBOKEN2=venv\Lib\site-packages\shiboken2\__init__.py
FastFlix.exe
```

### Development

#### Windows

You will need `pywin32`, I use the precompiled binaries from "https://www.lfd.uci.edu/~gohlke/pythonlibs"


