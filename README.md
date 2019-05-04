[![Build status](https://ci.appveyor.com/api/projects/status/208k29cvoq8xwf8j/branch/master?svg=true)](https://ci.appveyor.com/project/cdgriffith/fastflix/branch/master)

# FastFlix

FastFlix is a AV1 encoder, GIF maker, and general command wrapper. 

It can encode videos into AV1, GIF, and VP9, and is easily extendable! 

Read more about it and the licensing in the [docs](docs/README.md) folder.

# Plugins

Included plugins:

* AV1 (SVT-AV1)
* AV1 (FFMPEG libaom - currently very slow)
* VP9
* GIF

The plugins are extracted to `C:\Users\<username>\AppData\Roaming\FastFlix\<version>\pluigins`, and you can build or include your own. 

# Releases 

View the [releases](https://github.com/cdgriffith/FastFlix/releases) for 64 bit Windows binaries (Generated via Appveyor and also [available there](https://ci.appveyor.com/project/cdgriffith/fastflix)). 

# License

Copyright (C) 2019 Chris Griffith

This software is licensed under the MIT which you can read in the `LICENSE` file.

This software dynamically links PySide2 which is [LGPLv3 licensed](https://doc.qt.io/qt-5/lgpl.html) and can change the 
library used by specifying two environment variables, `SHIBOKEN2` and `PYSIDE2` which must point to the `__init__.py` file for the respective libraries. 

