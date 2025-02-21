# -*- coding: utf-8 -*-
import logging
from typing import List, Tuple, Union
from pathlib import Path

from box import Box
from PySide6 import QtGui, QtWidgets

from fastflix.exceptions import FastFlixInternalException
from fastflix.language import t
from fastflix.models.fastflix_app import FastFlixApp
from fastflix.widgets.background_tasks import ExtractHDR10
from fastflix.resources import group_box_style, get_icon


logger = logging.getLogger("fastflix")

ffmpeg_extra_command = ""

pix_fmts = ["8-bit: yuv420p", "10-bit: yuv420p10le", "12-bit: yuv420p12le"]

recommended_bitrates = [
    "150k  ",
    "276k  ",
    "512k  ",
    "1024k",
    "1800k",
    "3000k",
    "4000k",
    "5000k",
    "6000k",
    "7500k",
    "9000k",
    "10000k",
    "12000k",
    "15000k",
    "17500k",
    "20000k",
    "25000k",
    "30000k",
    "40000k",
    "50000k",
    "Custom",
]

recommended_qp = [
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "Custom",
]


class SettingPanel(QtWidgets.QWidget):
    def __init__(self, parent, main, app: FastFlixApp, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.main = main
        self.app = app
        self.widgets = Box()
        self.labels = Box()
        self.opts = Box()
        self.only_int = QtGui.QIntValidator()

    def close(self) -> bool:
        for widget, item in self.widgets.items():
            self.widgets[widget] = None
        del self.widgets
        del self.labels
        del self.opts
        return super().close()

    def paintEvent(self, event):
        o = QtWidgets.QStyleOption()
        o.initFrom(self)
        p = QtGui.QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, o, p, self)

    @staticmethod
    def translate_tip(tooltip):
        return "\n".join([t(x) for x in tooltip.split("\n") if x.strip()])

    def determine_default(self, widget_name, opt, items: List, raise_error: bool = False):
        if widget_name == "pix_fmt":
            items = [x.split(":")[1].strip() for x in items]
        elif widget_name in ("crf", "qp", "qscale"):
            if not opt:
                return 6
            opt = str(opt)
            items = [x.split("(")[0].split("-")[0].strip() for x in items]
        elif widget_name == "bitrate":
            if not opt:
                return 5
            items = [x.split("(")[0].split("-")[0].strip() for x in items]
        elif widget_name == "gpu":
            if opt == -1:
                return 0
        if isinstance(opt, str):
            try:
                return items.index(opt)
            except Exception:
                if raise_error:
                    raise FastFlixInternalException
                else:
                    logger.error(f"Could not set default for {widget_name} to {opt} as it's not in the list: {items}")
                return 0
        if isinstance(opt, bool):
            return int(opt)
        return opt

    def _add_combo_box(
        self,
        options,
        widget_name,
        label=None,
        opt=None,
        connect="default",
        enabled=True,
        default=0,
        tooltip="",
        min_width=None,
        width=None,
    ):
        layout = QtWidgets.QHBoxLayout()
        if label:
            self.labels[widget_name] = QtWidgets.QLabel(t(label))
            if tooltip:
                self.labels[widget_name].setToolTip(self.translate_tip(tooltip))

        self.widgets[widget_name] = QtWidgets.QComboBox()
        self.widgets[widget_name].addItems(options)
        if min_width:
            self.widgets[widget_name].setMinimumWidth(min_width)
        if width:
            self.widgets[widget_name].setFixedWidth(width)

        if opt:
            default = self.determine_default(
                widget_name, self.app.fastflix.config.encoder_opt(self.profile_name, opt), options
            )
            self.opts[widget_name] = opt
        else:
            logger.warning("No opt provided for widget %s %s", self.__class__.__name__, widget_name)
        self.widgets[widget_name].setCurrentIndex(default or 0)
        self.widgets[widget_name].setDisabled(not enabled)
        new_width = self.widgets[widget_name].minimumSizeHint().width() + 20
        if new_width > self.widgets[widget_name].view().width():
            self.widgets[widget_name].view().setFixedWidth(new_width)
        if tooltip:
            self.widgets[widget_name].setToolTip(self.translate_tip(tooltip))
        if connect:
            if connect == "default":
                self.widgets[widget_name].currentIndexChanged.connect(
                    lambda: self.main.page_update(build_thumbnail=False)
                )
            elif connect == "self":
                self.widgets[widget_name].currentIndexChanged.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].currentIndexChanged.connect(connect)

        if not label:
            return self.widgets[widget_name]

        layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])

        return layout

    def _add_text_box(
        self,
        label,
        widget_name,
        opt=None,
        connect="default",
        enabled=True,
        default="",
        tooltip="",
        validator=None,
        width=None,
        placeholder=None,
    ):
        layout = QtWidgets.QHBoxLayout()
        self.labels[widget_name] = QtWidgets.QLabel(t(label))
        if tooltip:
            self.labels[widget_name].setToolTip(self.translate_tip(tooltip))

        self.widgets[widget_name] = QtWidgets.QLineEdit()

        if placeholder:
            self.widgets[widget_name].setPlaceholderText(placeholder)

        if opt:
            default = str(self.app.fastflix.config.encoder_opt(self.profile_name, opt)) or default
            self.opts[widget_name] = opt
        else:
            logger.warning("No opt provided for widget %s %s", self.__class__.__name__, widget_name)

        self.widgets[widget_name].setText(default)
        self.widgets[widget_name].setDisabled(not enabled)
        if tooltip:
            self.widgets[widget_name].setToolTip(self.translate_tip(tooltip))
        if connect:
            if connect == "default":
                self.widgets[widget_name].textChanged.connect(lambda: self.main.page_update(build_thumbnail=False))
            elif connect == "self":
                self.widgets[widget_name].textChanged.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].textChanged.connect(connect)

        if validator:
            if validator == "int":
                self.widgets[widget_name].setValidator(self.only_int)
            if validator == "float":
                self.widgets[widget_name].setValidator(self.only_int)

        if width:
            self.widgets[widget_name].setFixedWidth(width)

        layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])

        return layout

    def _add_check_box(self, label, widget_name, opt, connect="default", enabled=True, tooltip=""):
        layout = QtWidgets.QHBoxLayout()

        self.widgets[widget_name] = QtWidgets.QCheckBox(t(label))
        self.opts[widget_name] = opt
        self.widgets[widget_name].setChecked(self.app.fastflix.config.encoder_opt(self.profile_name, opt))
        self.widgets[widget_name].setDisabled(not enabled)
        if tooltip:
            self.widgets[widget_name].setToolTip(self.translate_tip(tooltip))
        if connect:
            if connect == "default":
                self.widgets[widget_name].toggled.connect(lambda: self.main.page_update(build_thumbnail=False))
            elif connect == "self":
                self.widgets[widget_name].toggled.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].toggled.connect(connect)

        # layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])

        return layout

    def _add_custom(self, title="Custom ffmpeg options", connect="default", disable_both_passes=False):
        layout = QtWidgets.QHBoxLayout()
        self.labels.ffmpeg_options = QtWidgets.QLabel(t(title))
        self.labels.ffmpeg_options.setToolTip(t("Extra flags or options, cannot modify existing settings"))
        layout.addWidget(self.labels.ffmpeg_options)
        self.ffmpeg_extras_widget = QtWidgets.QLineEdit()
        self.ffmpeg_extras_widget.setText(ffmpeg_extra_command)
        self.widgets["extra_both_passes"] = QtWidgets.QCheckBox(t("Both Passes"))
        self.opts["extra_both_passes"] = "extra_both_passes"

        if connect and connect != "default":
            self.ffmpeg_extras_widget.disconnect()
            if connect == "self":
                connect = lambda: self.page_update()
            self.ffmpeg_extras_widget.textChanged.connect(connect)
            self.widgets["extra_both_passes"].toggled.connect(connect)
        else:
            self.ffmpeg_extras_widget.textChanged.connect(lambda: self.ffmpeg_extra_update())
            self.widgets["extra_both_passes"].toggled.connect(lambda: self.main.page_update(build_thumbnail=False))
        layout.addWidget(self.ffmpeg_extras_widget)
        if not disable_both_passes:
            layout.addWidget(self.widgets["extra_both_passes"])
        return layout

    def _add_file_select(self, label, widget_name, button_action, connect="default", enabled=True, tooltip=""):
        layout = QtWidgets.QHBoxLayout()
        self.labels[widget_name] = QtWidgets.QLabel(t(label))
        self.labels[widget_name].setToolTip(tooltip)

        self.widgets[widget_name] = QtWidgets.QLineEdit()
        self.widgets[widget_name].setDisabled(not enabled)
        self.widgets[widget_name].setToolTip(tooltip)

        self.opts[widget_name] = widget_name

        if connect:
            if connect == "default":
                self.widgets[widget_name].textChanged.connect(lambda: self.main.page_update(build_thumbnail=False))
            elif connect == "self":
                self.widgets[widget_name].textChanged.connect(lambda: self.page_update())
            else:
                self.widgets[widget_name].textChanged.connect(connect)

        button = QtWidgets.QPushButton(icon=QtGui.QIcon(get_icon("onyx-file-search", self.app.fastflix.config.theme)))
        button.clicked.connect(button_action)

        layout.addWidget(self.labels[widget_name])
        layout.addWidget(self.widgets[widget_name])
        layout.addWidget(button)
        return layout

    def extract_hdr10plus(self):
        self.extract_button.hide()
        self.extract_label.show()
        self.movie.start()
        # self.extracting_hdr10 = True
        self.extract_thrad = ExtractHDR10(
            self.app, self.main, signal=self.hdr10plus_signal, ffmpeg_signal=self.hdr10plus_ffmpeg_signal
        )
        self.extract_thrad.start()

    def done_hdr10plus_extract(self, metadata: str):
        self.extract_button.show()
        self.extract_label.hide()
        self.movie.stop()
        if Path(metadata).exists():
            self.widgets.hdr10plus_metadata.setText(metadata)
        self.ffmpeg_level.setText("")

    def dhdr10_update(self):
        dirname = Path(self.widgets.hdr10plus_metadata.text()).parent
        if not dirname.exists():
            dirname = Path()
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self, caption="hdr10_metadata", dir=str(dirname), filter="HDR10+ Metadata (*.json)"
        )
        if not filename or not filename[0]:
            return
        self.widgets.hdr10plus_metadata.setText(filename[0])
        self.main.page_update()

    def _add_modes(
        self,
        recommended_bitrates,
        recommended_qps,
        qp_name="crf",
        add_qp=True,
        disable_custom_qp=False,
        show_bitrate_passes=False,
        disable_bitrate=False,
    ):
        self.recommended_bitrates = recommended_bitrates
        self.recommended_qps = recommended_qps
        self.qp_name = qp_name
        layout = QtWidgets.QGridLayout()
        qp_group_box = QtWidgets.QGroupBox()
        qp_group_box.setStyleSheet(group_box_style())
        qp_box_layout = QtWidgets.QHBoxLayout()
        bitrate_group_box = QtWidgets.QGroupBox()
        bitrate_group_box.setStyleSheet(group_box_style())
        bitrate_box_layout = QtWidgets.QHBoxLayout()
        self.widgets.mode = QtWidgets.QButtonGroup()
        self.widgets.mode.buttonClicked.connect(self.set_mode)
        qp_help = (
            f"{qp_name.upper()} {t('is extremely source dependant')},\n"
            f"{t('the resolution-to-')}{qp_name.upper()}{t('are mere suggestions!')}"
        )
        config_opt = None
        if not disable_bitrate:
            self.bitrate_radio = QtWidgets.QRadioButton("Bitrate")
            self.bitrate_radio.setFixedWidth(80)
            self.widgets.mode.addButton(self.bitrate_radio)
            self.widgets.bitrate = QtWidgets.QComboBox()
            self.widgets.bitrate.addItems(recommended_bitrates)
            self.widgets.bitrate_passes = QtWidgets.QComboBox()
            self.widgets.bitrate_passes.addItems(["1", "2"])
            self.widgets.bitrate_passes.setCurrentIndex(1)
            self.widgets.bitrate_passes.currentIndexChanged.connect(lambda: self.mode_update())
            config_opt = self.app.fastflix.config.encoder_opt(self.profile_name, "bitrate")
            custom_bitrate = False
            try:
                default_bitrate_index = self.determine_default(
                    "bitrate", config_opt, recommended_bitrates, raise_error=True
                )
            except FastFlixInternalException:
                custom_bitrate = True
                self.widgets.bitrate.setCurrentText("Custom")
            else:
                self.widgets.bitrate.setCurrentIndex(default_bitrate_index)
            self.widgets.bitrate.currentIndexChanged.connect(lambda: self.mode_update())
            self.widgets.custom_bitrate = QtWidgets.QLineEdit("3000" if not custom_bitrate else config_opt)
            self.widgets.custom_bitrate.setValidator(QtGui.QDoubleValidator())
            self.widgets.custom_bitrate.setFixedWidth(100)
            self.widgets.custom_bitrate.setEnabled(custom_bitrate)
            self.widgets.custom_bitrate.textChanged.connect(lambda: self.main.build_commands())
            self.widgets.custom_bitrate.setValidator(self.only_int)
            bitrate_box_layout.addWidget(self.bitrate_radio)
            bitrate_box_layout.addWidget(self.widgets.bitrate, 1)
            bitrate_box_layout.addStretch(1)
            if show_bitrate_passes:
                bitrate_box_layout.addWidget(QtWidgets.QLabel(t("Passes") + ":"))
                bitrate_box_layout.addWidget(self.widgets.bitrate_passes)
            bitrate_box_layout.addStretch(1)
            bitrate_box_layout.addWidget(QtWidgets.QLabel(t("Custom") + ":"))
            bitrate_box_layout.addWidget(self.widgets.custom_bitrate)
            bitrate_box_layout.addWidget(QtWidgets.QLabel("k"))

            self.qp_radio = QtWidgets.QRadioButton(qp_name.upper())
            self.qp_radio.setChecked(True)
            self.qp_radio.setFixedWidth(80)
            self.qp_radio.setToolTip(qp_help)
            self.widgets.mode.addButton(self.qp_radio)

        self.widgets[qp_name] = QtWidgets.QComboBox()
        self.widgets[qp_name].setToolTip(qp_help)
        self.widgets[qp_name].addItems(recommended_qps)
        custom_qp = False
        qp_value = self.app.fastflix.config.encoder_opt(self.profile_name, qp_name)
        try:
            default_qp_index = self.determine_default(qp_name, qp_value, recommended_qps, raise_error=True)
        except FastFlixInternalException:
            if not disable_custom_qp:
                custom_qp = True
                self.widgets[qp_name].setCurrentText("Custom")
        else:
            if default_qp_index is not None:
                self.widgets[qp_name].setCurrentIndex(default_qp_index)

        self.widgets[qp_name].currentIndexChanged.connect(lambda: self.mode_update())
        if not disable_custom_qp:
            self.widgets[f"custom_{qp_name}"] = QtWidgets.QLineEdit("30" if not custom_qp else str(qp_value))
            self.widgets[f"custom_{qp_name}"].setFixedWidth(100)
            self.widgets[f"custom_{qp_name}"].setValidator(QtGui.QDoubleValidator())
            self.widgets[f"custom_{qp_name}"].setEnabled(custom_qp)
            self.widgets[f"custom_{qp_name}"].textChanged.connect(lambda: self.main.build_commands())

        if not disable_bitrate and config_opt:
            self.mode = "Bitrate"
            self.qp_radio.setChecked(False)
            self.bitrate_radio.setChecked(True)
        if not disable_bitrate:
            qp_box_layout.addWidget(self.qp_radio)
        qp_box_layout.addWidget(self.widgets[qp_name], 1)
        qp_box_layout.addStretch(1)
        qp_box_layout.addStretch(1)
        if disable_custom_qp:
            qp_box_layout.addStretch(1)
        else:
            qp_box_layout.addWidget(QtWidgets.QLabel("Custom:"))
            qp_box_layout.addWidget(self.widgets[f"custom_{qp_name}"])
        qp_box_layout.addWidget(QtWidgets.QLabel("  "))

        if not disable_bitrate:
            bitrate_group_box.setLayout(bitrate_box_layout)
        qp_group_box.setLayout(qp_box_layout)

        layout.addWidget(qp_group_box, 0, 0)
        if not disable_bitrate:
            layout.addWidget(bitrate_group_box, 1, 0)

        if not add_qp:
            qp_group_box.hide()

        return layout

    def set_mode(self):
        raise NotImplementedError("Child must implement this function")

    @property
    def ffmpeg_extras(self):
        return ffmpeg_extra_command

    def ffmpeg_extra_update(self):
        global ffmpeg_extra_command
        ffmpeg_extra_command = self.ffmpeg_extras_widget.text().strip()
        self.main.page_update(build_thumbnail=False)

    def new_source(self):
        if not self.app.fastflix.current_video or not self.app.fastflix.current_video.streams:
            return

    def update_profile(self):
        global ffmpeg_extra_command
        for widget_name, opt in self.opts.items():
            if isinstance(self.widgets[widget_name], QtWidgets.QComboBox):
                default = self.determine_default(
                    widget_name,
                    self.app.fastflix.config.encoder_opt(self.profile_name, opt),
                    [self.widgets[widget_name].itemText(i) for i in range(self.widgets[widget_name].count())],
                )
                if default is not None:
                    self.widgets[widget_name].setCurrentIndex(default)
            elif isinstance(self.widgets[widget_name], QtWidgets.QCheckBox):
                checked = self.app.fastflix.config.encoder_opt(self.profile_name, opt)
                if checked is not None:
                    self.widgets[widget_name].setChecked(checked)
            elif isinstance(self.widgets[widget_name], QtWidgets.QLineEdit):
                data = self.app.fastflix.config.encoder_opt(self.profile_name, opt)
                if widget_name in ("x265_params", "svtav1_params", "vvc_params"):
                    data = ":".join(data)
                self.widgets[widget_name].setText(str(data) or "")
        try:
            bitrate = self.app.fastflix.config.encoder_opt(self.profile_name, "bitrate")
        except AttributeError:
            pass
        else:
            if bitrate:
                self.mode = "Bitrate"
                self.qp_radio.setChecked(False)
                self.bitrate_radio.setChecked(True)
                for i, rec in enumerate(self.recommended_bitrates):
                    if rec.startswith(bitrate):
                        self.widgets.bitrate.setCurrentIndex(i)
                        break
                else:
                    self.widgets.bitrate.setCurrentText("Custom")
                    self.widgets.custom_bitrate.setText(bitrate.rstrip("kKmMgGbB"))
            else:
                self.mode = self.qp_name
                self.qp_radio.setChecked(True)
                self.bitrate_radio.setChecked(False)
                qp = str(self.app.fastflix.config.encoder_opt(self.profile_name, self.qp_name))
                for i, rec in enumerate(self.recommended_qps):
                    if rec.split(" ")[0] == qp:
                        self.widgets[self.qp_name].setCurrentIndex(i)
                        break
                else:
                    self.widgets[self.qp_name].setCurrentText("Custom")
                    self.widgets[f"custom_{self.qp_name}"].setText(qp)
        ffmpeg_extra_command = self.app.fastflix.config.encoder_opt(self.profile_name, "extra")
        self.ffmpeg_extras_widget.setText(ffmpeg_extra_command)

    def init_max_mux(self):
        return self._add_combo_box(
            label="Max Muxing Queue Size",
            tooltip='Useful when you have the "Too many packets buffered for output stream" error',
            widget_name="max_mux",
            options=["default", "1024", "2048", "4096", "8192"],
            opt="max_muxing_queue_size",
        )

    def reload(self):
        """This will reset the current settings to what is set in "current_video", useful for return from queue"""
        global ffmpeg_extra_command
        logger.debug("Update reload called")
        self.updating_settings = True
        for widget_name, opt in self.opts.items():
            data = getattr(self.app.fastflix.current_video.video_settings.video_encoder_settings, opt)
            if isinstance(self.widgets[widget_name], QtWidgets.QComboBox):
                if widget_name == "pix_fmt":
                    for fmt in pix_fmts:
                        if fmt.endswith(data):
                            self.widgets[widget_name].setCurrentText(fmt)
                if isinstance(data, int):
                    self.widgets[widget_name].setCurrentIndex(data)
                else:
                    self.widgets[widget_name].setCurrentText(data)
                    # Do smart check for cleaning up stuff

            elif isinstance(self.widgets[widget_name], QtWidgets.QCheckBox):
                self.widgets[widget_name].setChecked(data)
            elif isinstance(self.widgets[widget_name], QtWidgets.QLineEdit):
                if widget_name in ("x265_params", "svtav1_params", "vvc_params"):
                    data = ":".join(data)
                self.widgets[widget_name].setText(str(data) or "")
        if getattr(self, "mode", None):
            bitrate = getattr(self.app.fastflix.current_video.video_settings.video_encoder_settings, "bitrate", None)
            if bitrate:
                self.mode = "Bitrate"
                self.qp_radio.setChecked(False)
                self.bitrate_radio.setChecked(True)
                for i, rec in enumerate(self.recommended_bitrates):
                    if rec.startswith(bitrate):
                        self.widgets.bitrate.setCurrentIndex(i)
                        break
                else:
                    self.widgets.bitrate.setCurrentText("Custom")
                    self.widgets.custom_bitrate.setText(bitrate.rstrip("k"))
            else:
                self.mode = self.qp_name
                try:
                    self.qp_radio.setChecked(True)
                    self.bitrate_radio.setChecked(False)
                except Exception:
                    pass
                qp = str(getattr(self.app.fastflix.current_video.video_settings.video_encoder_settings, self.qp_name))
                for i, rec in enumerate(self.recommended_qps):
                    if rec.startswith(qp):
                        self.widgets[self.qp_name].setCurrentIndex(i)
                        break
                else:
                    self.widgets[self.qp_name].setCurrentText("Custom")
                    self.widgets[f"custom_{self.qp_name}"].setText(qp)
        ffmpeg_extra_command = self.app.fastflix.current_video.video_settings.video_encoder_settings.extra
        self.ffmpeg_extras_widget.setText(ffmpeg_extra_command)
        self.updating_settings = False

    def get_mode_settings(self) -> Tuple[str, Union[float, int, str]]:
        if self.mode.lower() == "bitrate":
            bitrate = self.widgets.bitrate.currentText()
            if bitrate.lower() == "custom":
                if not bitrate:
                    logger.error("No custom bitrate provided, defaulting to 3000k")
                    return "bitrate", "3000k"
                bitrate = self.widgets.custom_bitrate.text().lower().rstrip("k")
                bitrate += "k"
            else:
                bitrate = bitrate.split(" ", 1)[0]
            return "bitrate", bitrate
        else:
            qp_text = self.widgets[self.qp_name].currentText()
            if qp_text.lower() == "custom":
                custom_value = self.widgets[f"custom_{self.qp_name}"].text()
                if not custom_value:
                    logger.error("No value provided for custom QP/CRF value, defaulting to 30")
                    return "qp", 30
                try:
                    custom_value = float(self.widgets[f"custom_{self.qp_name}"].text().rstrip("."))
                except ValueError:
                    logger.error("Custom QP/CRF value is not a number, defaulting to 30")
                    return "qp", 30
                if custom_value.is_integer():
                    custom_value = int(custom_value)
                return "qp", custom_value
            else:
                return "qp", int(qp_text.split(" ", 1)[0])

    def init_pix_fmt(self, supported_formats=pix_fmts):
        return self._add_combo_box(
            label="Bit Depth",
            tooltip="Pixel Format (requires at least 10-bit for HDR)",
            widget_name="pix_fmt",
            options=supported_formats,
            opt="pix_fmt",
        )


class RigayaPanel(SettingPanel):
    def init_decoder(self):
        return self._add_combo_box(
            widget_name="decoder",
            label="Decoder",
            options=["Auto", "Hardware", "Software"],
            opt="decoder",
            tooltip="Hardware: use libavformat + hardware decoder for input\nSoftware: use avcodec + software decoder",
            min_width=80,
        )

    def init_dhdr10_info(self):
        layout = self._add_check_box(
            label="Copy HDR10+",
            widget_name="copy_hdr10",
            tooltip="Copy HDR10+ dynamic metadata from input file",
            opt="copy_hdr10",
        )
        return layout


class QSVEncPanel(RigayaPanel):
    def init_adapt_ref(self):
        return self._add_check_box(
            label="Adaptive Reference Frames",
            tooltip="Adaptively select list of reference frames to improve encoding quality.",
            widget_name="adapt_ref",
            opt="adapt_ref",
        )

    def init_adapt_ltr(self):
        return self._add_check_box(
            label="Adaptive Long-Term Reference Frames",
            tooltip="Mark, modify, or remove LTR frames based on encoding parameters and content properties.",
            widget_name="adapt_ltr",
            opt="adapt_ltr",
        )

    def init_adapt_cqm(self):
        return self._add_check_box(
            label="Adaptive CQM",
            tooltip="Adaptively select one of implementation-defined quantization matrices for each frame, to improve subjective visual quality under certain conditions.",
            widget_name="adapt_cqm",
            opt="adapt_cqm",
        )


class VCEPanel(RigayaPanel):
    def init_pa_row(self):
        #     pa_caq_strength: str | None = None
        #     pa_initqpsc: int | None = None
        #     pa_lookahead: int | None = None
        #     pa_fskip_maxqp: int | None = None
        #     pa_ltr: bool = False
        #     pa_paq: str | None = None
        #     pa_taq: int | None = None
        #     pa_motion_quality: str | None = None

        self.pa_row_1 = QtWidgets.QHBoxLayout()
        self.pa_row_2 = QtWidgets.QHBoxLayout()
        self.pa_area = QtWidgets.QVBoxLayout()

        self.labels["pa_row1"] = QtWidgets.QLabel(f"       {t('Pre Analysis')}")
        self.labels["pa_row2"] = QtWidgets.QLabel(f"       {t('8-Bit Only')}")

        self.pa_row_1.addWidget(self.labels["pa_row1"])
        self.pa_row_2.addWidget(self.labels["pa_row2"])

        self.pa_row_1.addStretch(1)
        self.pa_row_2.addStretch(1)

        self.pa_row_1.addLayout(
            self._add_combo_box(
                label="Scene Change",
                tooltip="Scene change detection method",
                widget_name="pa_sc",
                options=["none", "low", "medium", "high"],
                opt="pa_sc",
            )
        )
        self.pa_row_1.addStretch(1)
        self.pa_row_1.addLayout(
            self._add_combo_box(
                label="Static Scene",
                tooltip="Sensitivity of static scene detection",
                options=["none", "low", "medium", "high"],
                widget_name="pa_ss",
                opt="pa_ss",
            )
        )
        self.pa_row_1.addStretch(1)
        self.pa_row_1.addLayout(
            self._add_combo_box(
                label="Activity Type",
                tooltip="Activity type detection method",
                options=["none", "y", "yuv"],
                widget_name="pa_activity_type",
                opt="pa_activity_type",
            )
        )
        self.pa_row_1.addStretch(1)
        self.pa_row_1.addLayout(
            self._add_combo_box(
                opt="pa_caq_strength",
                widget_name="pa_caq_strength",
                label="CAQ Strength",
                tooltip="Strength of CAQ",
                options=["low", "medium", "high"],
            )
        )
        self.pa_row_1.addStretch(1)
        self.pa_row_1.addLayout(
            self._add_combo_box(
                opt="pa_initqpsc",
                widget_name="pa_initqpsc",
                label="SC QP",
                tooltip="Initial qp after scene change",
                options=[t("Auto")] + [str(i) for i in range(1, 51)],
            )
        )
        self.pa_row_1.addStretch(1)
        self.pa_row_1.addLayout(
            self._add_combo_box(
                opt="pa_lookahead",
                widget_name="pa_lookahead",
                label="Lookahead",
                tooltip="Lookahead distance",
                options=[t("Auto")] + [str(i) for i in range(1, 200)],
            )
        )

        self.pa_row_2.addLayout(
            self._add_text_box(
                opt="pa_fskip_maxqp",
                widget_name="pa_fskip_maxqp",
                label="FSkip Max QP",
                tooltip="Threshold to insert skip frame on static scene",
            )
        )
        self.pa_row_2.addStretch(1)
        self.pa_row_2.addLayout(
            self._add_check_box(
                opt="pa_ltr",
                widget_name="pa_ltr",
                label="LTR",
                tooltip="Enable long-term reference frame",
            )
        )
        self.pa_row_2.addStretch(1)
        self.pa_row_2.addLayout(
            self._add_combo_box(
                opt="pa_paq",
                widget_name="pa_paq",
                label="PAQ",
                tooltip="Perceptual AQ mode",
                options=["none", "caq"],
            )
        )
        self.pa_row_2.addStretch(1)
        self.pa_row_2.addLayout(
            self._add_combo_box(
                opt="pa_taq",
                widget_name="pa_taq",
                label="TAQ",
                tooltip="Temporal AQ mode",
                options=["Auto", "0", "1", "2"],
            )
        )
        self.pa_row_2.addStretch(1)
        self.pa_row_2.addLayout(
            self._add_combo_box(
                opt="pa_motion_quality",
                widget_name="pa_motion_quality",
                label="Motion Quality",
                tooltip="High motion quality boost mode",
                options=["none", "auto"],
            )
        )
        self.pa_changed()
        self.pa_area.addLayout(self.pa_row_1)
        self.pa_area.addLayout(self.pa_row_2)

    def pa_changed(self):
        for widget in self.widgets:
            if widget.startswith("pa_"):
                self.widgets[widget].setEnabled(self.widgets["pre_analysis"].isChecked())
                if self.widgets["pre_analysis"].isChecked():
                    self.widgets[widget].show()
                    if widget in self.labels:
                        self.labels[widget].show()
                else:
                    self.widgets[widget].hide()
                    if widget in self.labels:
                        self.labels[widget].hide()
        if self.widgets["pre_analysis"].isChecked():
            self.labels["pa_row1"].show()
            self.labels["pa_row2"].show()
        else:
            self.labels["pa_row1"].hide()
            self.labels["pa_row2"].hide()

    def init_output_depth(self):
        return self._add_combo_box(
            label="Output Depth",
            widget_name="output_depth",
            tooltip="Output Depth",
            options=[t("Auto"), "8", "10"],
            opt="output_depth",
        )


class VAAPIPanel(SettingPanel):
    def init_rc_mode(self):
        # #   -rc_mode           <int>        E..V....... Set rate control mode (from 0 to 6) (default auto)
        # #      auto            0            E..V....... Choose mode automatically based on other parameters
        # #      CQP             1            E..V....... Constant-quality
        # #      CBR             2            E..V....... Constant-bitrate
        # #      VBR             3            E..V....... Variable-bitrate
        # #      ICQ             4            E..V....... Intelligent constant-quality
        # #      QVBR            5            E..V....... Quality-defined variable-bitrate
        # #      AVBR            6            E..V....... Average variable-bitrate
        return self._add_combo_box(
            label="Rate Control Mode",
            tooltip="Set rate control mode",
            options=["auto", "CQP", "CBR", "VBR", "ICQ", "QVBR", "AVBR"],
            widget_name="rc_mode",
            opt="rc_mode",
        )

    def init_level(self):
        return self._add_combo_box(
            label="Level",
            tooltip="Set level (general_level_idc)",
            options=["auto", "1", "2", "2.1", "3", "3.1", "4", "4.1", "5", "5.1", "5.2", "6", "6.1", "6.2"],
            widget_name="level",
            opt="level",
        )

    def init_aud(self):
        return self._add_check_box(
            label="AUD",
            tooltip="Include AUD",
            widget_name="aud",
            opt="aud",
        )

    def init_async_depth(self):
        return self._add_combo_box(
            label="Async Depth",
            tooltip="Maximum processing parallelism. Increase this to improve single channel performance. This option doesn't work if driver doesn't implement vaSyncBuffer function.",
            options=[str(i) for i in range(1, 65)],
            widget_name="async_depth",
            opt="async_depth",
            default="2",
            width=40,
        )

    def init_b_depth(self):
        return self._add_text_box(
            label="B Depth",
            tooltip="Maximum B-frame reference depth (from 1 to INT_MAX) (default 1)",
            widget_name="b_depth",
            opt="b_depth",
            default="1",
            width=40,
        )

    def init_idr_interval(self):
        return self._add_text_box(
            label="IDR Interval",
            tooltip="Distance between IDR frames (from 0 to INT_MAX) (default 0)",
            widget_name="idr_interval",
            opt="idr_interval",
            default="0",
            width=40,
        )

    def init_low_power(self):
        return self._add_check_box(
            label="Low Power Mode", tooltip="Enable low power mode", widget_name="low_power", opt="low_power"
        )

    def init_modes(self):
        layout = self._add_modes(recommended_bitrates, recommended_qp, qp_name="qp")
        return layout

    def init_vaapi_device(self):
        return self._add_text_box(
            label="VA-API Device",
            tooltip="VA-API device to use (default /dev/dri/renderD128)",
            widget_name="vaapi_device",
            opt="vaapi_device",
            default="/dev/dri/renderD128",
            width=200,
        )
