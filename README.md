# FastFlix

![preview](./docs/gui_preview.png)

FastFlix is a simple and friendly GUI for encoding videos.

FastFlix keeps HDR10 metadata for x265, which will be expanded to AV1 libraries when available.

It needs `FFmpeg` (version 4.3 or greater) under the hood for the heavy lifting, and can work with a variety of encoders.

Check out [the FastFlix github wiki](https://github.com/cdgriffith/FastFlix/wiki) for help or more details!

#  Encoders

 FastFlix supports the following encoders when their required libraries are found in FFmpeg:

* HEVC (libx265) &nbsp;&nbsp;&nbsp; <img src="./fastflix/data/encoders/icon_x265.png" height="30" alt="x265" >
* AVC (libx264) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <img src="./fastflix/data/encoders/icon_x264.png" height="30" alt="x264" >
* AV1 (librav1e) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <img src="./fastflix/data/encoders/icon_rav1e.png" height="30" alt="rav1e" >
* AV1 (libaom-av1) &nbsp; <img src="./fastflix/data/encoders/icon_av1_aom.png" height="30" alt="av1_aom" >
* AV1 (libsvtav1) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <img src="./fastflix/data/encoders/icon_svt_av1.png" height="30" alt="svt_av1" >
* VP9 (libvpx) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <img src="./fastflix/data/encoders/icon_vp9.png" height="30" alt="vpg" >
* WEBP (libwebp) &nbsp;&nbsp;&nbsp;<img src="./fastflix/data/encoders/icon_webp.png" height="30" alt="vpg" >
* GIF (gif) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <img src="./fastflix/data/encoders/icon_gif.png" height="30" alt="gif" >

All of these are currently supported by [BtbN's Windows FFmpeg builds](https://github.com/BtbN/FFmpeg-Builds) which is the default FFmpeg downloaded.

Most other builds do not have all these encoders available by default and may require custom compiling FFmpeg for a specific encoder.

* [Windows FFmpeg (and more) auto builder](https://github.com/m-ab-s/media-autobuild_suite)
* [Windows cross compile FFmpeg (build on linux)](https://github.com/rdp/ffmpeg-windows-build-helpers)
* [FFmpeg compilation guide](https://trac.ffmpeg.org/wiki/CompilationGuide)

# Releases

## Windows
[![Build status](https://ci.appveyor.com/api/projects/status/208k29cvoq8xwf8j/branch/master?svg=true)](https://ci.appveyor.com/project/cdgriffith/fastflix/branch/master)

View the [releases](https://github.com/cdgriffith/FastFlix/releases) for 64 bit Windows binaries (Generated via Appveyor and also [available there](https://ci.appveyor.com/project/cdgriffith/fastflix)).

## MacOS and Linux

Due to a recent library addition there have been unexpected dependencies on *nix systems that will try to be removed in future versions.

**MacOS** You will need to have Xcode installed  
**Linux** Please install `gcc` and python3 development files (`python3-dev` on Ubuntu, `python3-devel` on RedHat)

Then please use [pipx](https://pipxproject.github.io/pipx/installation/) to install as a properly virtualized app

```
pipx install fastflix
```

You will need to have `ffmpeg` and `ffprobe` executables on your PATH and they must be executable. Version 4.3 or greater is required. The one in your in your package manager system may not support all encoders or options.
Check out the [FFmpeg download page for static builds](https://ffmpeg.org/download.html) for Linux and Mac.

## Running from source code

```
git clone https://github.com/cdgriffith/FastFlix.git
cd FastFlix
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python -m fastflix
```

# HDR

On any 10-bit or higher video output, FastFlix will copy the input HDR colorspace (bt2020). Which is [different than HDR10 or HDR10+](https://codecalamity.com/hdr-hdr10-hdr10-hlg-and-dolby-vision/).

## HDR10

FastFlix was created to easily extract / copy HDR10 data, but as of sept 2020, only x265 support copying that data through FFmpeg, no AV1 library does.

VP9 has limited support to copy some existing HDR10 metadata, usually from other VP9 files. Will have the line "Mastering Display Metadata, has_primaries:1 has_luminance:1 ..." when it works.

* rav1e -  can set mastering data and CLL via their CLI but [not through ffmpeg](https://github.com/xiph/rav1e/issues/2554).
* SVT AV1 - accepts a "--enable-hdr" flag that is [not well documented](https://github.com/AOMediaCodec/SVT-AV1/blob/master/Docs/svt-av1_encoder_user_guide.md), not supported through FFmpeg.
* aomenc (libaom-av1) - does not look to support HDR10

## HDR10+

FastFlix supports using generated or [extracted JSON HDR10+ Metadata](https://github.com/cdgriffith/FastFlix/wiki/HDR10-Plus-Metadata-Extraction) with HEVC encodes via x265. However that is highly
dependant on a FFmpeg version that has been compiled with x265 that has HDR10+ support. [BtbN's Windows FFmpeg builds](https://github.com/BtbN/FFmpeg-Builds) 
have this support as of 10/23/2020 and may require a [manual upgrade](https://github.com/cdgriffith/FastFlix/wiki/Updating-FFmpeg).

## Dolby Vision

FastFlix does not plan to support Dolby Visions proprietary format, as it requires royalties.


# License

Copyright (C) 2019-2020 Chris Griffith

The code itself is licensed under the MIT which you can read in the `LICENSE` file. <br>
Read more about the release licensing in the [docs](docs/README.md) folder. <br>
Encoder icons for [VP9](https://commons.wikimedia.org/wiki/File:Vp9-logo-for-mediawiki.svg) and [AOM AV1](https://commons.wikimedia.org/wiki/File:AV1_logo_2018.svg) are from Wikimedia Commons all others are self created.
