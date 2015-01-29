from PyQt4 import QtCore, QtGui
import cfgdialog_ui
import coluse_ui
import colsave_ui
import errordialog_ui
import deriveddialog_ui
import confirmdialog_ui

class cfgdialog(QtGui.QDialog):
    def __init__(self, model, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = cfgdialog_ui.Ui_Dialog()
        self.ui.setupUi(self)
        self.model = model
      
    def exec_(self, prompt, idx=None):
        self.ui.label.setText(prompt)
        t = self.model.setupTree(self.ui.treeWidget, "ditem")
        if idx != None:
            self.ui.treeWidget.setCurrentItem(t[idx]['ditem'])
            self.ui.treeWidget.expandItem(t[idx]['ditem'])
        code = QtGui.QDialog.exec_(self)
        if code == QtGui.QDialog.Accepted:
            try:
                self.result = self.ui.treeWidget.currentItem().id
            except:
                return QtGui.QDialog.Rejected  # No selection made!
        return code

class colusedialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = coluse_ui.Ui_Dialog()
        self.ui.setupUi(self)

class colsavedialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = colsave_ui.Ui_Dialog()
        self.ui.setupUi(self)

class errordialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = errordialog_ui.Ui_Dialog()
        self.ui.setupUi(self)

class confirmdialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = confirmdialog_ui.Ui_Dialog()
        self.ui.setupUi(self)

class deriveddialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.ui = deriveddialog_ui.Ui_deriveddialog()
        self.ui.setupUi(self)
        self.buttonlist = []

    def reset(self):
        for b in self.buttonlist:
            self.ui.verticalLayout_2.removeWidget(b)
            b.setParent(None)
        self.buttonlist = []

    def addValue(self, s, v):
        b = QtGui.QRadioButton(s, self)
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
        return QtGui.QDialog.exec_(self)
