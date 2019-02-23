# FastFlix

FastFlix is a current and next-gen video encoder. 

It can encode videos in AV1, and extended to use x265 with a GPL build of ffmpeg. 

Read more about it and the licensing in the [docs](docs/README.md)

# Releases 

View the [releases](https://github.com/cdgriffith/FastFlix/releases) for Windows and Linux binaries (Generated via Appveyor and also [available there](https://ci.appveyor.com/project/cdgriffith/fastflix)). 

For legal reasons the ffmpeg binary cannot be bundled with the executable and must be [separately downloaded](https://www.ffmpeg.org/download.html).

## Setting up ffmpeg

There are three ways provided a path to ffmpeg. 

1. Looks in the FFMPEG and FFPROBE environment variables
2. Looks on the system PATH to see if it is already available
3. Manually link to the directory housing the binary files via the GUI 

## Running the code locally

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

