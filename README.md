[![Build status](https://ci.appveyor.com/api/projects/status/208k29cvoq8xwf8j/branch/master?svg=true)](https://ci.appveyor.com/project/cdgriffith/fastflix/branch/master)

# FastFlix

FastFlix is a AV1 and HEVC encoder, GIF maker, and general ffmpeg command wrapper.

It can encode videos into HEVC, AV1, GIF, and VP9, and is easily extendable!

Read more about it and the licensing in the [docs](docs/README.md) folder.

![preview](https://raw.githubusercontent.com/cdgriffith/binary-files/fast-flix/media/fastflix/2.0.0/main.png)


# Encoders

Currently there is support for:

* HEVC (libx265)
* AV1 (SVT-AV1)
* AV1 (FFMPEG libaom - currently very slow)
* VP9
* GIF


# Releases

## Windows
View the [releases](https://github.com/cdgriffith/FastFlix/releases) for 64 bit Windows binaries (Generated via Appveyor and also [available there](https://ci.appveyor.com/project/cdgriffith/fastflix)).

## MacOS and Linux

Please use [pipx](https://pipxproject.github.io/pipx/installation/) to install as a properly virtualized app

```
pipx install fastflix
```

## Running from source code or without pipx

```
git clone https://github.com/cdgriffith/FastFlix.git
cd FastFlix
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python -m flix
```

# License

Copyright (C) 2019-2020 Chris Griffith

This software is licensed under the MIT which you can read in the `LICENSE` file.

This software dynamically links PySide2 which is [LGPLv3 licensed](https://doc.qt.io/qt-5/lgpl.html) and can change the
library used by specifying two environment variables, `SHIBOKEN2` and `PYSIDE2` which must point to the `__init__.py` file for the respective libraries.

