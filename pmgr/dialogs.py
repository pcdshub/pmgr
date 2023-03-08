from __future__ import annotations

import functools
import pathlib

from PyQt5 import QtCore, QtWidgets, uic

MODULE_PATH = pathlib.Path(__file__).resolve().parent


@functools.lru_cache(maxsize=None)
def load_ui_file(filename: str) -> type[QtWidgets.QWidget]:
    """
    Load the .ui file ``filename`` and return its widget class.

    Parameters
    ----------
    filename : str
        The filename of the .ui file, relative to the pmgr source directory.

    Returns
    -------
    subclass of QtWidgets.QWidget
    """
    cls, _ = uic.loadUiType(MODULE_PATH / filename)
    return cls


class cfgdialog(QtWidgets.QDialog):
    def __init__(self, model, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = load_ui_file("cfgdialog.ui")()
        self.ui.setupUi(self)
        self.model = model

    def exec_(self, prompt, idx=None):
        self.ui.label.setText(prompt)
        t = self.model.setupTree(self.ui.treeWidget, "ditem")
        if idx is not None:
            self.ui.treeWidget.setCurrentItem(t[idx]["ditem"])
            self.ui.treeWidget.expandItem(t[idx]["ditem"])
        code = QtWidgets.QDialog.exec_(self)
        if code == QtWidgets.QDialog.Accepted:
            try:
                self.result = self.ui.treeWidget.currentItem().id
            except Exception:
                return QtWidgets.QDialog.Rejected  # No selection made!
        return code


class colusedialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = load_ui_file("coluse.ui")()
        self.ui.setupUi(self)


class colsavedialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = load_ui_file("colsave.ui")()
        self.ui.setupUi(self)


class errordialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = load_ui_file("errordialog.ui")()
        self.ui.setupUi(self)


class confirmdialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = load_ui_file("confirmdialog.ui")()
        self.ui.setupUi(self)


class deriveddialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = load_ui_file("deriveddialog.ui")()
        self.ui.setupUi(self)
        self.buttonlist = []

    def reset(self):
        for b in self.buttonlist:
            self.ui.verticalLayout_2.removeWidget(b)
            b.setParent(None)
        self.buttonlist = []

    def addValue(self, s, v):
        b = QtWidgets.QRadioButton(s, self)
        if self.buttonlist == []:
            b.setChecked(True)
        b.return_value = v
        self.buttonlist.append(b)
        self.ui.verticalLayout_2.addWidget(b)

    def getValue(self):
        for b in self.buttonlist:
            if b.isChecked():
                return b.return_value

    def fixSize(self):
        self.resize(0, 0)

    def exec_(self):
        # MCB - This is an ugly hack.  I should figure out how to do it properly.
        QtCore.QTimer.singleShot(100, self.fixSize)
        return QtWidgets.QDialog.exec_(self)


class chowndialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = load_ui_file("chown.ui")()
        self.ui.setupUi(self)

    def exec_(self, cfg, hutch, hutchlist):
        self.ui.mainLabel.setText(
            "Current owner of {} is {}.".format(cfg, hutch.upper())
        )
        self.ui.comboBox.clear()
        for i in hutchlist:
            if i != hutch:
                self.ui.comboBox.addItem(i.upper())
        code = QtWidgets.QDialog.exec_(self)
        if code == QtWidgets.QDialog.Accepted:
            try:
                self.result = self.ui.comboBox.currentText().lower()
            except Exception:
                return QtWidgets.QDialog.Rejected  # No selection made!
        return code
