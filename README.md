[![Build status](https://ci.appveyor.com/api/projects/status/208k29cvoq8xwf8j/branch/master?svg=true)](https://ci.appveyor.com/project/cdgriffith/fastflix/branch/master)

# FastFlix

FastFlix is a simple and friendly GUI for encoding videos.

![preview](https://raw.githubusercontent.com/cdgriffith/binary-files/fast-flix/media/fastflix/2.0.0/main.png)

It uses `FFmpeg` under the hood for the heavy lifting, and can work with a variety of encoders.

#  Encoders

<img src="./fastflix/data/encoders/icon_x265.png" height="100" alt="x265" >
<img src="./fastflix/data/encoders/icon_x264.png" height="100" alt="x264" >
<img src="./fastflix/data/encoders/icon_av1_aom.png" height="100" alt="av1_aom" >
<img src="./fastflix/data/encoders/icon_rav1e.png" height="100" alt="rav1e" >
<img src="./fastflix/data/encoders/icon_svt_av1.png" height="100" alt="svt_av1" >
<img src="./fastflix/data/encoders/icon_vp9.png" height="100" alt="vpg" >
<img src="./fastflix/data/encoders/icon_gif.png" height="100" alt="gif" >

Currently FastFlix supports the following encoders if their required libraries are in FFmpeg:

* HEVC (libx265)
* AVC (libx264)
* AV1 (libaom-av1, libsvtav1, librav1e)
* VP9 (libvpx)
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
