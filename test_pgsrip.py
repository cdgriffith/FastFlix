# -*- coding: utf-8 -*-
from pgsrip import pgsrip, Mkv, Options
from babelfish import Language

video = r"F:/Uncompressed Videos/Blade/Blade (1998) [imdbid-tt0120611]/Blade_t00.mkv"
media = Mkv(video)
options = Options(languages={Language("eng")}, overwrite=True, one_per_lang=True)

pgsrip.rip(media, options)
