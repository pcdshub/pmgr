from PyQt4 import QtCore, QtGui
import cfgdialog_ui
import coluse_ui
import colsave_ui
import errordialog_ui

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
