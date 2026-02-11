# -*- coding: utf-8 -*-
from PySide6 import QtWidgets, QtCore

from fastflix.language import t, language

TERMS_SECTIONS = [
    ("FastFlix Terms and Agreements", ""),
    ("By using FastFlix, you agree to the following terms:", ""),
    (
        "1. Authorized Use Only",
        "You must only use FastFlix to encode, transcode, or otherwise process video "
        "content that you own or have the legal rights to use. Unauthorized copying, "
        "encoding, or distribution of copyrighted material is strictly prohibited.",
    ),
    (
        "2. No Developer Liability for Misuse",
        "The developers and contributors of FastFlix are not responsible for any misuse "
        "of this software, including but not limited to the unauthorized reproduction or "
        "distribution of copyrighted content. You assume full responsibility for how you "
        "use FastFlix.",
    ),
    (
        "3. No Warranty",
        'FastFlix is provided "as-is" without warranty of any kind, express or implied, '
        "including but not limited to the warranties of merchantability, fitness for a "
        "particular purpose, and non-infringement.",
    ),
    (
        "4. Copyright Compliance",
        "You assume all responsibility for compliance with applicable copyright laws and "
        "regulations in your jurisdiction. It is your obligation to ensure that your use "
        "of FastFlix does not violate any third-party rights.",
    ),
    (
        "5. Limitation of Liability",
        "In no event shall the developers or contributors of FastFlix be liable for any "
        "damages arising from the use of this software, including but not limited to "
        "direct, indirect, incidental, special, or consequential damages.",
    ),
]


def _build_terms_text(translate_fn):
    parts = []
    for header, body in TERMS_SECTIONS:
        if body:
            parts.append(f"{translate_fn(header)}\n{translate_fn(body)}")
        else:
            parts.append(translate_fn(header))
    return "\n\n".join(parts)


class TermsAgreementDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("FastFlix Terms and Agreements"))
        self.setMinimumSize(550, 450)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        layout = QtWidgets.QVBoxLayout(self)

        english_text = _build_terms_text(lambda x: x)
        if language != "eng":
            translated_text = _build_terms_text(t)
            display_text = translated_text + "\n\n" + ("─" * 58) + "\n\n" + english_text
        else:
            display_text = english_text

        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(display_text)
        layout.addWidget(text_edit)

        self.agree_checkbox = QtWidgets.QCheckBox(t("I have read and agree to the Terms and Agreements"))
        self.agree_checkbox.stateChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.agree_checkbox)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = QtWidgets.QPushButton(t("Accept"))
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)

        cancel_button = QtWidgets.QPushButton(t("Reject"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _on_checkbox_changed(self, state):
        self.ok_button.setEnabled(state == QtCore.Qt.CheckState.Checked.value)

    def reject(self):
        super().reject()

    def closeEvent(self, event):
        self.reject()
        event.accept()
