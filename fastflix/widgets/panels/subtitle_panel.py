#!/usr/bin/env python
# -*- coding: utf-8 -*-

from box import Box

from fastflix.shared import QtGui, QtCore, QtWidgets, error_message, main_width
from fastflix.widgets.panels.abstract_list import FlixList

dispositions = [
    "none",
    "default",
    "dub",
    "original",
    "comment",
    "lyrics",
    "karaoke",
    "forced",
    "hearing_impaired",
]

languages = (
    "aar,abk,ace,ach,ada,ady,afh,afr,ain,aka,akk,ale,alt,amh,ang,anp,ara,arc,arg,arn,arp,arw,asm,ast,ava,ave,"
    "awa,aym,aze,bak,bal,bam,ban,bas,bej,bel,bem,ben,bho,bik,bin,bis,bla,bod,bos,bra,bre,bua,bug,bul,byn,cad,"
    "car,cat,ceb,ces,cha,chb,che,chg,chk,chm,chn,cho,chp,chr,chu,chv,chy,cop,cor,cos,cre,crh,csb,cym,dak,dan,"
    "dar,del,den,deu,dgr,din,div,doi,dsb,dua,dum,dyu,dzo,efi,egy,eka,ell,elx,eng,enm,epo,est,eus,ewe,ewo,fan,"
    "fao,fas,fat,fij,fil,fin,fon,fra,frm,fro,frr,frs,fry,ful,fur,gaa,gay,gba,gez,gil,gla,gle,glg,glv,gmh,goh,"
    "gon,gor,got,grb,grc,grn,gsw,guj,gwi,hai,hat,hau,haw,heb,her,hil,hin,hit,hmn,hmo,hrv,hsb,hun,hup,hye,iba,"
    "ibo,ido,iii,iku,ile,ilo,ina,ind,inh,ipk,isl,ita,jav,jbo,jpn,jpr,jrb,kaa,kab,kac,kal,kam,kan,kas,kat,kau,"
    "kaw,kaz,kbd,kha,khm,kho,kik,kin,kir,kmb,kok,kom,kon,kor,kos,kpe,krc,krl,kru,kua,kum,kur,kut,lad,lah,lam,"
    "lao,lat,lav,lez,lim,lin,lit,lol,loz,ltz,lua,lub,lug,lui,lun,luo,lus,mad,mag,mah,mai,mak,mal,man,mar,mas,"
    "mdf,mdr,men,mga,mic,min,mis,mkd,mlg,mlt,mnc,mni,moh,mon,mos,mri,msa,mul,mus,mwl,mwr,mya,myv,nap,nau,nav,"
    "nbl,nde,ndo,nds,nep,new,nia,niu,nld,nno,nob,nog,non,nor,nqo,nso,nwc,nya,nym,nyn,nyo,nzi,oci,oji,ori,orm,"
    "osa,oss,ota,pag,pal,pam,pan,pap,pau,peo,phn,pli,pol,pon,por,pro,pus,que,raj,rap,rar,roh,rom,ron,run,rup,"
    "rus,sad,sag,sah,sam,san,sas,sat,scn,sco,sel,sga,shn,sid,sin,slk,slv,sma,sme,smj,smn,smo,sms,sna,snd,snk,"
    "sog,som,sot,spa,sqi,srd,srn,srp,srr,ssw,suk,sun,sus,sux,swa,swe,syc,syr,tah,tam,tat,tel,tem,ter,tet,tgk,"
    "tgl,tha,tig,tir,tiv,tkl,tlh,tli,tmh,tog,ton,tpi,tsi,tsn,tso,tuk,tum,tur,tvl,twi,tyv,udm,uga,uig,ukr,umb,"
    "und,urd,uzb,vai,ven,vie,vol,vot,wal,war,was,wln,wol,xal,xho,yao,yap,yid,yor,zap,zbl,zen,zgh,zha,zho,zul,"
    "zun,zxx,zza"
)

language_list = languages.split(",")


class Subtitle(QtWidgets.QTabWidget):
    def __init__(self, parent, subtitle, index, enabled=True, first=False):
        self.loading = True
        super(Subtitle, self).__init__(parent)
        self.parent = parent
        self.index = index
        self.outdex = None
        self.subtitle = Box(subtitle, default_box=True)
        self.first = first
        self.last = False
        self.subtitle_lang = subtitle.get("tags", {}).get("language")

        self.widgets = Box(
            track_number=QtWidgets.QLabel(f"{self.index}:{self.outdex}" if enabled else "❌"),
            title=QtWidgets.QLabel(f"  {self.subtitle.codec_long_name}"),
            up_button=QtWidgets.QPushButton("^"),
            down_button=QtWidgets.QPushButton("v"),
            enable_check=QtWidgets.QCheckBox("Preserve"),
            disposition=QtWidgets.QComboBox(),
            language=QtWidgets.QComboBox(),
        )

        self.widgets.disposition.addItems(dispositions)
        self.widgets.enable_check.setChecked(enabled)
        self.widgets.enable_check.toggled.connect(self.update_enable)
        self.widgets.disposition.currentIndexChanged.connect(self.page_update)
        self.widgets.disposition.setCurrentIndex(0)
        for disposition, is_set in self.subtitle.disposition.items():
            if is_set:
                try:
                    self.widgets.disposition.setCurrentIndex(dispositions.index(disposition))
                except ValueError:
                    pass  # TODO figure out all possible dispositions for subtitles / log if issue
                break

        self.setFixedHeight(60)

        disposition_layout = QtWidgets.QHBoxLayout()
        disposition_layout.addStretch()
        disposition_layout.addWidget(QtWidgets.QLabel("Disposition"))
        disposition_layout.addWidget(self.widgets.disposition)

        grid = QtWidgets.QGridLayout()
        grid.addLayout(self.init_move_buttons(), 0, 0)
        grid.addWidget(self.widgets.track_number, 0, 1)
        grid.addWidget(self.widgets.title, 0, 2)
        grid.addLayout(disposition_layout, 0, 4)
        grid.addLayout(self.init_language(), 0, 5)
        grid.addWidget(self.widgets.enable_check, 0, 6)

        self.setLayout(grid)
        self.loading = False

    def init_move_buttons(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        # self.widgets.up_button = QtWidgets.QPushButton("^")
        self.widgets.up_button.setDisabled(self.first)
        self.widgets.up_button.setFixedWidth(20)
        self.widgets.up_button.clicked.connect(lambda: self.parent.move_up(self))
        # self.widgets.down_button = QtWidgets.QPushButton("v")
        self.widgets.down_button.setDisabled(self.last)
        self.widgets.down_button.setFixedWidth(20)
        self.widgets.down_button.clicked.connect(lambda: self.parent.move_down(self))
        layout.addWidget(self.widgets.up_button)
        layout.addWidget(self.widgets.down_button)
        return layout

    def init_language(self):
        self.widgets.language.addItems(language_list)
        try:
            self.widgets.language.setCurrentIndex(language_list.index(self.subtitle_lang))
        except Exception:
            self.widgets.language.setCurrentIndex(language_list.index("eng"))

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Language"))
        layout.addWidget(self.widgets.language)
        return layout

    def set_first(self, first=True):
        self.first = first
        self.widgets.up_button.setDisabled(self.first)

    def set_last(self, last=True):
        self.last = last
        self.widgets.down_button.setDisabled(self.last)

    def set_outdex(self, outdex):
        self.outdex = outdex
        if not self.enabled:
            self.widgets.track_number.setText("❌")
        else:
            self.widgets.track_number.setText(f"{self.index}:{self.outdex}")

    @property
    def disposition(self):
        text = self.widgets.disposition.currentText()
        return 0 if text == "none" else text

    @property
    def enabled(self):
        return self.widgets.enable_check.isChecked()

    @property
    def language(self):
        return self.widgets.language.currentText()

    def update_enable(self):
        enabled = self.widgets.enable_check.isChecked()
        self.widgets.track_number.setText(f"{self.index}:{self.outdex}" if enabled else "❌")
        self.parent.reorder()
        self.page_update()

    def page_update(self):
        if not self.loading:
            return self.parent.main.page_update()


class SubtitleList(FlixList):
    def __init__(self, parent, starting_pos=0):
        super().__init__(parent, "Subtitle Tracks", starting_pos)
        self.main = parent.main

    def new_source(self, starting_pos=0):
        self.starting_pos = starting_pos
        self.tracks = []
        for index, track in enumerate(self.main.streams.subtitle):
            new_item = Subtitle(self, track, index=track.index, first=True if index == 0 else False)
            self.tracks.append(new_item)
        if self.tracks:
            self.tracks[0].set_first()
            self.tracks[-1].set_last()

        super()._new_source(self.tracks)

    def get_settings(self):
        tracks = []
        for track in self.tracks:
            if track.enabled:
                tracks.append(
                    {
                        "index": track.index,
                        "outdex": track.outdex,
                        "disposition": track.disposition,
                        "language": track.language,
                    }
                )
        return Box(subtitle_tracks=tracks)
