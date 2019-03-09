[![Build status](https://ci.appveyor.com/api/projects/status/208k29cvoq8xwf8j/branch/master?svg=true)](https://ci.appveyor.com/project/cdgriffith/fastflix/branch/master)

# FastFlix

FastFlix is a GIF converter as well as current and next-gen video encoder. 

It can encode videos into AV1, GIF, and can be extended to use x265 with a GPL build of ffmpeg. 

Read more about it and the licensing in the [docs](docs/README.md)

# Releases 

View the [releases](https://github.com/cdgriffith/FastFlix/releases) for 64 bit Windows binaries (Generated via Appveyor and also [available there](https://ci.appveyor.com/project/cdgriffith/fastflix)). 

## Running the code locally

Requires Python 3.6 or greater. 

Download and extract the [latest zip](https://github.com/cdgriffith/FastFlix/archive/master.zip). Then run the following.

```
pip install requirements.txt
python -m flix
```

You will need [ffmpeg](https://www.ffmpeg.org/download.html) and [SVT AV1](https://github.com/OpenVisualCloud/SVT-AV1) executables.

# License

Copyright (C) 2019 Chris Griffith

This software is licensed under the MIT which you can read in the `LICENSE` file.

This software dynamically links PySide2 which is [LGPLv3 licensed](https://doc.qt.io/qt-5/lgpl.html) and can change the 
library used by specifying two environment variables, `SHIBOKEN2` and `PYSIDE2` which must point to the `__init__.py` file for the respective libraries. 

