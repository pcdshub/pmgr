#!/usr/bin/env python
import sys
import threading

from PyQt5 import QtCore, QtGui, QtWidgets
from psp.options import Options

from .pmgr_ui import Ui_MainWindow
from .ObjModel import ObjModel
from .CfgModel import CfgModel
from .db import db
from .MyDelegate import MyDelegate
from . import dialogs
from . import param
from . import auth_ui
from . import utils

######################################################################

class authdialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
      QtWidgets.QWidget.__init__(self, parent)
      self.ui = auth_ui.Ui_Dialog()
      self.ui.setupUi(self)

######################################################################

class GraphicUserInterface(QtWidgets.QMainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.authdialog = authdialog(self)
        self.utimer = QtCore.QTimer()
        
        param.params.ui = Ui_MainWindow()
        ui = param.params.ui

        ui.setupUi(self)

        # Not sure how to do this in designer, so we put it randomly and move it now.
        ui.statusbar.addWidget(ui.userLabel)
        self.setUser(param.params.myuid)
        
        self.setWindowTitle("Parameter Manager for %s (%s)" % (param.params.hutch.upper(), param.params.table))

        ui.objectTable.verticalHeader().hide()
        ui.objectTable.setCornerButtonEnabled(False)
        ui.objectTable.horizontalHeader().setSectionsMovable(True)

        ui.configTable.verticalHeader().hide()
        ui.configTable.setCornerButtonEnabled(False)
        ui.configTable.horizontalHeader().setSectionsMovable(True)

        param.params.db = db()
        
        ui.menuView.addAction(ui.configWidget.toggleViewAction())
        ui.configWidget.setWindowTitle(param.params.table + " configurations")
        param.params.cfgmodel = CfgModel()
        ui.configTable.init(param.params.cfgmodel, 0, param.params.cfgmodel.mutable)
        ui.configTable.setShowGrid(True)
        ui.configTable.resizeColumnsToContents()
        ui.configTable.setItemDelegate(MyDelegate(self))

        ui.menuView.addAction(ui.objectWidget.toggleViewAction())
        ui.objectWidget.setWindowTitle(param.params.table + " objects")
        param.params.objmodel = ObjModel()
        ui.objectTable.init(param.params.objmodel, 0, param.params.objmodel.mutable)
        ui.objectTable.setShowGrid(True)
        ui.objectTable.resizeColumnsToContents()
        ui.objectTable.setSortingEnabled(True)
        ui.objectTable.sortByColumn(param.params.objmodel.pvcol, QtCore.Qt.AscendingOrder)
        ui.objectTable.setItemDelegate(MyDelegate(self))

        param.params.objmodel.setupContextMenus(ui.objectTable)
        param.params.cfgmodel.setupContextMenus(ui.configTable)

        param.params.cfgdialog       = dialogs.cfgdialog(param.params.cfgmodel, self)
        param.params.colsavedialog   = dialogs.colsavedialog(self)
        param.params.colusedialog    = dialogs.colusedialog(self)
        param.params.deriveddialog   = dialogs.deriveddialog(self)
        param.params.confirmdialog   = dialogs.confirmdialog(self)
        param.params.chowndialog     = dialogs.chowndialog(self)

        param.params.db.objchange.connect(param.params.objmodel.objchange)
        param.params.db.cfgchange.connect(param.params.objmodel.cfgchange)
        param.params.db.cfgchange.connect(param.params.cfgmodel.cfgchange)

        param.params.cfgmodel.newname.connect(param.params.cfgmodel.haveNewName)
        param.params.cfgmodel.newname.connect(param.params.objmodel.haveNewName)
        param.params.cfgmodel.cfgChanged.connect(param.params.objmodel.cfgEdit)

        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(param.params.table)
        v = settings.value("geometry")
        if v is not None:
            self.restoreGeometry(v)
        v = settings.value("windowState")
        if v is not None:
            self.restoreState(v)
        v = settings.value("cfgcol/default")
        if v is not None:
            ui.configTable.restoreHeaderState(v)
        v = settings.value("objcol/default")
        if v is not None:
            ui.objectTable.restoreHeaderState(v)
        v = settings.value("objsel")
        if v is not None:
            param.params.objmodel.setObjSel(str(v))

        # MCB - Sigh.  I don't know why this is needed, but it is, otherwise the FreezeTable breaks.
        h = ui.configTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)
        h.resizeSection(1, h.sectionSize(1) - 1)
        h = ui.objectTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)
        h.resizeSection(1, h.sectionSize(1) - 1)

        ui.configTable.colmgr = "%s/cfgcol" % param.params.table
        ui.objectTable.colmgr = "%s/objcol" % param.params.table

        if param.params.debug:
            pass
        else:
            ui.debugButton.hide()
        ui.saveButton.clicked.connect(param.params.objmodel.commitall)
        ui.revertButton.clicked.connect(param.params.objmodel.revertall)
        if param.params.applyOK:
            ui.applyButton.clicked.connect(param.params.objmodel.applyall)
        else:
            ui.applyButton.hide()
        ui.actionProtected.triggered.connect(param.params.objmodel.doShow)
        ui.actionManual.triggered.connect(param.params.objmodel.doShow)
        ui.actionTrack.triggered.connect(param.params.objmodel.doTrack)
        ui.actionAuth.triggered.connect(self.doAuthenticate)
        ui.actionExit.triggered.connect(self.doExit)
        self.utimer.timeout.connect(self.unauthenticate)
        ui.objectTable.selectionModel().selectionChanged.connect(param.params.objmodel.selectionChanged)
        # MCB - Sigh. I should just make FreezeTableView actually work.
        ui.objectTable.cTV.selectionModel().selectionChanged.connect(param.params.objmodel.selectionChanged)

    def closeEvent(self, event):
        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(param.params.table)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("cfgcol/default", param.params.ui.configTable.saveHeaderState())
        settings.setValue("objcol/default", param.params.ui.objectTable.saveHeaderState())
        settings.setValue("objsel", param.params.objmodel.getObjSel())
        QtWidgets.QMainWindow.closeEvent(self, event)

    def doExit(self):
        self.close()

    def setUser(self, user):
        param.params.user = user
        param.params.ui.userLabel.setText("User: " + user)

    def authenticate_user(self, user="", password=""):
        if user == "":
            self.setUser(param.params.myuid)
            return True
        if utils.authenticate_user(user, password):
            self.setUser(user)
            self.utimer.start(10 * 60000) # Ten minutes!
            return True
        else:
            QtWidgets.QMessageBox.critical(None, "Error", "Invalid Password",
                                       QtWidgets.QMessageBox.Ok)
            return False

    def doAuthenticate(self):
        result = self.authdialog.exec_()
        user = str(self.authdialog.ui.nameEdit.text())
        password = str(self.authdialog.ui.passEdit.text())
        self.authdialog.ui.passEdit.setText("")
        if result == QtWidgets.QDialog.Accepted:
            if not self.authenticate_user(user, password):
                self.unauthenticate()

    def unauthenticate(self):
        self.utimer.stop()
        self.authenticate_user()
        

def main():
    #MCB QtWidgets.QApplication.setGraphicsSystem("raster")
    param.params = param.param_structure()
    app = QtWidgets.QApplication([''])
  
    # Options( [mandatory list, optional list, switches list] )
    options = Options(['hutch', 'type'], [], ['debug', 'applyenable', 'dev', 'help'])
    try:
        options.parse()
    except Exception as msg:
        options.usage(str(msg))
        sys.exit()

    if options.help is not None:
        options.usage(str(msg))
        sys.exit()

    param.params.setHutch(options.hutch.lower())
    param.params.setTable(options.type)
    param.params.debug = False if options.debug is None else True
    param.params.applyOK = False if options.applyenable is None else True
    param.params.prod = True if options.dev is None else False
    gui = GraphicUserInterface()
    param.params.setTable(options.type)  # Sigh, do this again to fix dropdown.
    # MCB - We need a better way of doing this.
    if options.type == "ims_motor":
        param.params.setCatEnum(["Beamline", "Dumb"]) # Displayed names.
    try:
        gui.show()
        retval = app.exec_()
    except KeyboardInterrupt:
        app.exit(1)
    sys.exit(retval)


if __name__ == '__main__':
    main()
