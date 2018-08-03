from . import cfgdialog_ui
from . import coluse_ui
from . import colsave_ui
from . import errordialog_ui
from . import deriveddialog_ui
from . import confirmdialog_ui
from . import chown_ui

from PyQt5 import QtCore, QtGui, QtWidgets


class cfgdialog(QtWidgets.QDialog):
    def __init__(self, model, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = cfgdialog_ui.Ui_Dialog()
        self.ui.setupUi(self)
        self.model = model
      
    def exec_(self, prompt, idx=None):
        self.ui.label.setText(prompt)
        t = self.model.setupTree(self.ui.treeWidget, "ditem")
        if idx != None:
            self.ui.treeWidget.setCurrentItem(t[idx]['ditem'])
            self.ui.treeWidget.expandItem(t[idx]['ditem'])
        code = QtWidgets.QDialog.exec_(self)
        if code == QtWidgets.QDialog.Accepted:
            try:
                self.result = self.ui.treeWidget.currentItem().id
            except:
                return QtWidgets.QDialog.Rejected  # No selection made!
        return code

class colusedialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = coluse_ui.Ui_Dialog()
        self.ui.setupUi(self)

class colsavedialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = colsave_ui.Ui_Dialog()
        self.ui.setupUi(self)

class errordialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = errordialog_ui.Ui_Dialog()
        self.ui.setupUi(self)

class confirmdialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = confirmdialog_ui.Ui_Dialog()
        self.ui.setupUi(self)

class deriveddialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = deriveddialog_ui.Ui_deriveddialog()
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
        self.ui = chown_ui.Ui_Dialog()
        self.ui.setupUi(self)

    def exec_(self, cfg, hutch, hutchlist):
        self.ui.mainLabel.setText("Current owner of %s is %s." % (cfg, hutch.upper()))
        self.ui.comboBox.clear()
        for i in hutchlist:
            if i != hutch:
                self.ui.comboBox.addItem(i.upper())
        code = QtWidgets.QDialog.exec_(self)
        if code == QtWidgets.QDialog.Accepted:
            try:
                self.result = self.ui.comboBox.currentText().lower()
            except:
                return QtWidgets.QDialog.Rejected  # No selection made!
        return code
