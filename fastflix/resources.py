# -*- coding: utf-8 -*-
from pathlib import Path

import pkg_resources

main_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icon.ico")).resolve())
language_file = str(Path(pkg_resources.resource_filename(__name__, "data/languages.yaml")).resolve())
dark_mode = Path(pkg_resources.resource_filename(__name__, "data/styles/dark_mode.qss")).resolve().read_text()
default_mode = Path(pkg_resources.resource_filename(__name__, "data/styles/default.qss")).resolve().read_text()


changes_file = Path(pkg_resources.resource_filename(__name__, "CHANGES")).resolve()
local_changes_file = Path(__file__).parent.parent / "CHANGES"


video_add_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/video-add.png")).resolve())
video_playlist_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/video-playlist.png")).resolve())
play_round_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/play-round.png")).resolve())
cinema_film_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/cinema-film.png")).resolve())
video_delete_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/video-delete.png")).resolve())
black_x_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/black-x.png")).resolve())
up_arrow_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/up-arrow.png")).resolve())
down_arrow_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/down-arrow.png")).resolve())
settings_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/setting.png")).resolve())
folder_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/folder.png")).resolve())
play_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/play.png")).resolve())
profile_add_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/text-document-add.png")).resolve())
edit_box_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/edit-box.png")).resolve())
copy_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/copy.png")).resolve())
warning_icon = str(Path(pkg_resources.resource_filename(__name__, "data/icons/warning-triangle.png")).resolve())
