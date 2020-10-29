# -*- coding: utf-8 -*-
from pathlib import Path
import pkg_resources

main_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icon.ico")).resolve())
language_file = str(Path(pkg_resources.resource_filename(__name__, "data/languages.yaml")).resolve())
