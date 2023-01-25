# FastFlix

![preview](./docs/gui_preview.png)

FastFlix is a simple and friendly GUI for encoding videos.

[Download latest release from Github](https://github.com/cdgriffith/FastFlix/releases/latest)

FastFlix keeps HDR10 metadata for x265, NVEncC HEVC, and VCEEncC HEVC, which will also be expanded to AV1 libraries when available.

It needs `FFmpeg` (version 4.3 or greater required, 5.0+ recommended) under the hood for the heavy lifting, and can work with a variety of encoders.

Join us on [discord](https://discord.gg/GUBFP6f)!

Check out [the FastFlix github wiki](https://github.com/cdgriffith/FastFlix/wiki) for help or more details, and please report bugs or ideas in the [github issue tracker](https://github.com/cdgriffith/FastFlix/issues)!

#  Encoders

## Software Encoders

| Encoder   | x265 | x264 | rav1e | AOM AV1 | SVT AV1 | VP9 |
|-----------|------|------|-------|---------|---------|-----|
| HDR10     | ✓    |      |       |         | ✓       | ✓*  |
| HDR10+    | ✓    |      |       |         |         |     |
| Audio     | ✓    |  ✓   | ✓     | ✓       | ✓       | ✓   |
| Subtitles | ✓    |  ✓   | ✓     | ✓       | ✓       |     |
| Covers    | ✓    |  ✓   | ✓     | ✓       | ✓       |     |
| bt.2020   | ✓    |   ✓  | ✓     | ✓       | ✓       | ✓   |

## Hardware Encoders 

These will require the appropriate hardware. Nvidia GPU for NVEnc, Intel GPU/CPU for QSVEnc, and AMD GPU for VCEEnc. 

Most of these are using [rigaya's hardware encoders](https://github.com/rigaya?tab=repositories) that must be downloaded separately, 
extracted to a directory of your choice, and then linked too in FastFlix Settings panel.

### AV1

Theis is only supported on the latest generation of graphics cards as of 2022, specifically the Intel Arc and Nvidia 4000 series. 

| Encoder   | [NVEncC AV1](https://github.com/rigaya/NVEnc/releases) | [QSVEncC AV!](https://github.com/rigaya/QSVEnc/releases) |
|-----------|--------------------------------------------------------|----------------------------------------------------------|
| HDR10     | ✓                                                      | ✓                                                        |
| HDR10+    | ✓                                                      | ✓                                                        |
| Audio     | ✓*                                                     | ✓*                                                       |
| Subtitles | ✓                                                      | ✓                                                        |
| Covers    |                                                        |                                                          |
| bt.2020   | ✓                                                      | ✓                                                        |

### HEVC / H.265

| Encoder   | NVENC HEVC | [NVEncC HEVC](https://github.com/rigaya/NVEnc/releases) | [VCEEncC HEVC](https://github.com/rigaya/VCEEnc/releases) | [QSVEncC HEVC](https://github.com/rigaya/QSVEnc/releases) |
|-----------|------------|---------------------------------------------------------|-----------------------------------------------------------|-----------------------------------------------------------|
| HDR10     |            | ✓                                                       | ✓                                                         | ✓                                                         |
| HDR10+    |            | ✓                                                       | ✓                                                         | ✓                                                         |
| Audio     | ✓          | ✓*                                                      | ✓*                                                        | ✓*                                                        |
| Subtitles | ✓          | ✓                                                       | ✓                                                         | ✓                                                         |
| Covers    | ✓          |                                                         |                                                           |                                                           |
| bt.2020   | ✓          | ✓                                                       | ✓                                                         | ✓                                                         |

### AVC / H.264

| Encoder   | [NVEncC AVC](https://github.com/rigaya/NVEnc/releases) | [VCEEncC AVC](https://github.com/rigaya/VCEEnc/releases) | [QSVEncC AVC](https://github.com/rigaya/QSVEnc/releases) |
|-----------|--------------------------------------------------------|----------------------------------------------------------|----------------------------------------------------------|
| HDR10     |                                                        |                                                          |                                                          |
| HDR10+    |                                                        |                                                          |                                                          |
| Audio     | ✓*                                                     | ✓*                                                       | ✓*                                                       |
| Subtitles | ✓                                                      | ✓                                                        | ✓                                                        |
| Covers    |                                                        |                                                          |                                                          |
| bt.2020   | ✓                                                      | ✓                                                        | ✓                                                        |

`✓ - Full support   |   ✓* - Limited support`




# Releases

View the [releases](https://github.com/cdgriffith/FastFlix/releases) for binaries for Windows, MacOS or Linux

You will need to have `ffmpeg` and `ffprobe` executables on your PATH and they must be executable. Version 4.3 or greater is required for most usage, latest master build is recommended and required for some features. The one in your package manager system may not support all encoders or options.
Check out the [FFmpeg download page for static builds](https://ffmpeg.org/download.html) for Linux and Mac.

# Additional Encoders

To use rigaya's [Nvidia NVENC](https://github.com/rigaya/NVEnc/releases), [AMD VCE](https://github.com/rigaya/VCEEnc/releases), and [Intel QSV](https://github.com/rigaya/QSVEnc/releases) encoders, download them and extract them to folder on your hard drive. 

Windows: Go into FastFlix's settings and select the corresponding EXE file for each of the encoders you want to use. 

Linux: Install the rpm or deb and restart FastFlix


## Running from source code

Requires python3.8+

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

FastFlix was created to easily extract / copy HDR10 data, which it can do with the above listed encoders (x265, NVEncC, VCEEncC, QSVEncC).

VP9 has limited support to copy some existing HDR10 metadata, usually from other VP9 files. Will have the line "Mastering Display Metadata, has_primaries:1 has_luminance:1 ..." when it works.

AV1 is still in development, and hopefully all encoder will support it in the future, but only SVT AV1 works through ffmpeg as of now for software encoders. 

* QSVEnc - Works! 
* NVEncC - Works!
* rav1e -  can set mastering data and CLL via their CLI but [not through ffmpeg](https://github.com/xiph/rav1e/issues/2554).
* SVT AV1 - Now supports HDR10 with latest master ffmpeg build, make sure to update before trying!
* aomenc (libaom-av1) - does not look to support HDR10

## HDR10+

For Windows users with dedicated graphics cards, the best thing to do is use a hardware encoder, as they all support HDR10+ currently!

FastFlix also supports using generated or [extracted JSON HDR10+ Metadata](https://github.com/cdgriffith/FastFlix/wiki/HDR10-Plus-Metadata-Extraction) with HEVC encodes via x265. However, that is highly
dependent on a FFmpeg version that has been compiled with x265 that has HDR10+ support. [BtbN's Windows FFmpeg builds](https://github.com/BtbN/FFmpeg-Builds) 
have this support as of 10/23/2020 and may require a [manual upgrade](https://github.com/cdgriffith/FastFlix/wiki/Updating-FFmpeg).

If you add HDR10+ metadata file, make sure the encoding log does NOT contain the line `x265 [warning]: –dhdr10-info disabled. Enable HDR10_PLUS in cmake` or else it is unsupported. 

## HLG 

FastFlix (v4.0.2+) passes through HLG color transfer information to everything except webp and GIF. 

## Dolby Vision

FastFlix does not plan to support Dolby Vision's proprietary format at this time.

# Support FastFlix

Check out the different ways you can help [support FastFlix](https://github.com/cdgriffith/FastFlix/wiki/Support-FastFlix)!

# License

Copyright (C) 2019-2023 Chris Griffith

The code itself is licensed under the MIT which you can read in the `LICENSE` file. <br>
Read more about the release licensing in the [docs](docs/README.md) folder. <br>

Custom icons designed by Joey Catt | Onyx Studios

Encoder icons for [VP9](https://commons.wikimedia.org/wiki/File:Vp9-logo-for-mediawiki.svg) and [AOM AV1](https://commons.wikimedia.org/wiki/File:AV1_logo_2018.svg) are from Wikimedia Commons all others are self created.

Additional button icons from [https://uxwing.com](https://uxwing.com)

Sample videos and thumbnail for preview image provided by [Jessica Payne](http://iamjessicapayne.com/)
