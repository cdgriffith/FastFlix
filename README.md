# FastFlix

FastFlix is a super simple converter and clip maker.

It is designed to work with ffmpeg with x265 support or an equivalent command line tool.

They are expected to be found via the system path or specified on startup via `FFMPEG` and `FFPROBE` env variables.

# Releases 

View the [releases](https://github.com/cdgriffith/FastFlix/releases) for Windows and Linux binaries (Generated via Appveyor and also [available there](https://ci.appveyor.com/project/cdgriffith/fastflix). 

For legal reasons the ffmpeg binary cannot bundled and must be [separately downloaded](https://www.ffmpeg.org/download.html).


## Running locally

Requires Python 3.6 or greater. 

Download and extract the [latest zip](https://github.com/cdgriffith/FastFlix/archive/master.zip). Then run the following.

```
pip install requirements.txt
python -m flix
```

# License

Copyright (C) 2019 Chris Griffith

This software is licensed under the MIT which you can read in the `LICENSE` file.

This software dynamically links PySide2 which is [LGPLv3 licensed](https://doc.qt.io/qt-5/lgpl.html) and can change the 
library used by specifying two environment variables, `SHIBOKEN2` and `PYSIDE2` which must point to the `__init__.py` file for the respective libraries. 

