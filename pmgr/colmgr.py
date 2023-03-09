from PyQt5 import QtCore, QtWidgets

from . import param, utils
from .dialogs import load_ui_file

#
# This is an attempt at a general purpose column manager for QTableViews.
# We have added a save/restoreHeaderState function to our FreezeTableView,
# because our headers are special.  In general though, we could just
# access the header's restoreState function directly here.
#
# We assume that the QTableView has an additional property, colmgr,
# that points to the group in which the settings should be saved/restored
# in our QSettings.  The QSettings parameters are in param.params.settings.
#


def addColumnManagerMenu(table, extra=[], hideOK=True, cfgOK=True):
    menu = utils.MyContextMenu()
    if hideOK:
        menu.addAction("Hide column", hidecol)
        menu.addAction("Reset columns", resetcol)
        menu.addAction("Run column chooser", choosecol)
    menu.addAction("Autosize columns", sizecol)
    if cfgOK:
        menu.addAction("Save column config", savecol)
        menu.addAction("Use column config", restorecol)
    for t, f in extra:
        menu.addAction(t, f)
    table.addHeaderContextMenu(menu)


def hidecol(table, index):
    table.horizontalHeader().hideSection(index)


def resetcol(table, index):
    for i in range(table.model().columnCount()):
        if table.isColumnHidden(i):
            table.showColumn(i)
    h = table.horizontalHeader()
    for i in range(table.model().columnCount()):
        if h.visualIndex(i) != i:
            h.moveSection(h.visualIndex(i), i)


def sizecol(table, index):
    table.resizeColumnsToContents()


def choosecol(table, index):
    m = table.model()
    h = table.horizontalHeader()
    try:
        d = m.colchoosedialog
    except Exception:
        d = QtWidgets.QDialog()
        d.ui = load_ui_file("colchoose.ui")()
        d.ui.setupUi(d)
        c = []
        for i in range(m.mutable):
            c.append(None)
        for i in range(m.mutable, m.columnCount()):
            cb = QtWidgets.QCheckBox(d)
            cb.setText(m.horizontalHeaderItem(i).text())
            c.append(cb)
            d.ui.gridLayout.addWidget(cb, (i - m.mutable) / 5, (i - m.mutable) % 5)
        d.ui.allButton.clicked.connect(lambda: doAllButton(d))
        d.ui.noneButton.clicked.connect(lambda: doNoneButton(d))
        d.cols = c
        d.resize(0, 0)
        m.colchoosedialog = d
    c = d.cols
    for i in range(m.mutable, m.columnCount()):
        c[i].setChecked(not h.isSectionHidden(i))
    if d.exec_() == QtWidgets.QDialog.Accepted:
        for i in range(m.mutable, m.columnCount()):
            if c[i].isChecked():
                h.showSection(i)
            else:
                h.hideSection(i)


def doAllButton(d):
    for c in d.cols:
        if c is not None:
            c.setChecked(True)


def doNoneButton(d):
    for c in d.cols:
        if c is not None:
            c.setChecked(False)


def savecol(table, index):
    d = param.params.colsavedialog
    d.ui.lineEdit.setText("")
    if d.exec_() == QtWidgets.QDialog.Accepted:
        cfg = str(d.ui.lineEdit.text())
        if cfg == "":
            # Complain!
            return
        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(table.colmgr)
        settings.setValue(cfg, table.saveHeaderState())


def restorecol(table, index):
    settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
    settings.beginGroup(table.colmgr)
    d = param.params.colusedialog
    d.ui.comboBox.clear()
    for x in list(settings.childKeys()):
        d.ui.comboBox.addItem(x)
    if d.exec_() == QtWidgets.QDialog.Accepted:
        cfg = str(d.ui.comboBox.currentText())
        v = settings.value(cfg)
        if v is not None:
            table.restoreHeaderState(v.toByteArray())
