[![Build status](https://ci.appveyor.com/api/projects/status/208k29cvoq8xwf8j/branch/master?svg=true)](https://ci.appveyor.com/project/cdgriffith/fastflix/branch/master)

# FastFlix

FastFlix is a AV1, HEVC (x265) and VP9 encoder, GIF maker, and general ffmpeg command wrapper.

![preview](https://raw.githubusercontent.com/cdgriffith/binary-files/fast-flix/media/fastflix/2.0.0/main.png)


# Encoders

Currently there is support for:

* HEVC (libx265)
* AV1 (SVT-AV1 on Windows)
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

## Running from source code

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

The code itself is licensed under the MIT which you can read in the `LICENSE` file.
Read more about the release licensing in the [docs](docs/README.md) folder.

