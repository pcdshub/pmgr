#!/usr/bin/env python
from PyQt4 import QtCore, QtGui
import sys
from psp.options import Options
from pmgr_ui import Ui_MainWindow
from ObjModel import ObjModel
from CfgModel import CfgModel
from GrpModel import GrpModel
import dialogs
import param
from db import db
import threading
from MyDelegate import MyDelegate
import auth_ui
import utils

######################################################################

class authdialog(QtGui.QDialog):
    def __init__(self, parent=None):
      QtGui.QWidget.__init__(self, parent)
      self.ui = auth_ui.Ui_Dialog()
      self.ui.setupUi(self)

######################################################################

class GraphicUserInterface(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)

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
        ui.objectTable.horizontalHeader().setMovable(True)

        ui.configTable.verticalHeader().hide()
        ui.configTable.setCornerButtonEnabled(False)
        ui.configTable.horizontalHeader().setMovable(True)

        ui.groupTable.verticalHeader().hide()
        ui.groupTable.setCornerButtonEnabled(False)
        ui.groupTable.horizontalHeader().setMovable(False)

        ui.groupWidget.close()

        param.params.db = db()
        
        ui.menuView.addAction(ui.configWidget.toggleViewAction())
        ui.configWidget.setWindowTitle(param.params.table + " configurations")
        param.params.cfgmodel = CfgModel()
        ui.configTable.init(param.params.cfgmodel, 0, 2)
        ui.configTable.setShowGrid(True)
        ui.configTable.resizeColumnsToContents()
        ui.configTable.setItemDelegate(MyDelegate(self))

        ui.menuView.addAction(ui.objectWidget.toggleViewAction())
        ui.objectWidget.setWindowTitle(param.params.table + " objects")
        param.params.objmodel = ObjModel()
        ui.objectTable.init(param.params.objmodel, 0, 2)
        ui.objectTable.setShowGrid(True)
        ui.objectTable.resizeColumnsToContents()
        ui.objectTable.setSortingEnabled(True)
        ui.objectTable.sortByColumn(param.params.objmodel.namecol, QtCore.Qt.AscendingOrder)
        ui.objectTable.setItemDelegate(MyDelegate(self))

        ui.menuView.addAction(ui.groupWidget.toggleViewAction())
        ui.groupWidget.setWindowTitle(param.params.table + " configuration groups")
        param.params.grpmodel = GrpModel()
        ui.groupTable.init(param.params.grpmodel, 0, 3)
        ui.groupTable.setShowGrid(True)
        ui.groupTable.resizeColumnsToContents()
        ui.groupTable.setSortingEnabled(False)
        ui.groupTable.setItemDelegate(MyDelegate(self))

        param.params.objmodel.setupContextMenus(ui.objectTable)
        param.params.cfgmodel.setupContextMenus(ui.configTable)
        param.params.grpmodel.setupContextMenus(ui.groupTable)

        param.params.cfgdialog       = dialogs.cfgdialog(param.params.cfgmodel, self)
        param.params.colsavedialog   = dialogs.colsavedialog(self)
        param.params.colusedialog    = dialogs.colusedialog(self)
        param.params.deriveddialog   = dialogs.deriveddialog(self)
        param.params.confirmdialog   = dialogs.confirmdialog(self)

        param.params.db.objchange.connect(param.params.objmodel.objchange)
        param.params.db.cfgchange.connect(param.params.objmodel.cfgchange)
        param.params.db.cfgchange.connect(param.params.cfgmodel.cfgchange)
        param.params.db.cfgchange.connect(param.params.grpmodel.cfgchange)
        param.params.db.grpchange.connect(param.params.grpmodel.grpchange)

        param.params.cfgmodel.newname.connect(param.params.cfgmodel.haveNewName)
        param.params.cfgmodel.newname.connect(param.params.objmodel.haveNewName)
        param.params.cfgmodel.cfgChanged.connect(param.params.objmodel.cfgEdit)

        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(param.params.table)
        self.restoreGeometry(settings.value("geometry").toByteArray())
        self.restoreState(settings.value("windowState").toByteArray())
        ui.configTable.restoreHeaderState(settings.value("cfgcol/default").toByteArray())
        ui.objectTable.restoreHeaderState(settings.value("objcol/default").toByteArray())
        ui.groupTable.restoreHeaderState(settings.value("grpcol/default").toByteArray())
        param.params.objmodel.setObjSel(str(settings.value("objsel").toByteArray()))

        # MCB - This is so if we have too many rows/columns in the save file,
        # we get rid of them.  Is this just a problem as we develop the group model
        # though?
        param.params.grpmodel.grpchange()

        # MCB - Sigh.  I don't know why this is needed, but it is, otherwise the FreezeTable breaks.
        h = ui.configTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)
        h.resizeSection(1, h.sectionSize(1) - 1)
        h = ui.objectTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)
        h.resizeSection(1, h.sectionSize(1) - 1)
        h = ui.groupTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)
        h.resizeSection(1, h.sectionSize(1) - 1)

        ui.configTable.colmgr = "%s/cfgcol" % param.params.table
        ui.objectTable.colmgr = "%s/objcol" % param.params.table
        ui.groupTable.colmgr = "%s/grpcol" % param.params.table

        if param.params.debug:
            self.connect(ui.debugButton,     QtCore.SIGNAL("clicked()"), param.params.grpmodel.doDebug)
        else:
            ui.debugButton.hide()
        self.connect(ui.saveButton,      QtCore.SIGNAL("clicked()"), param.params.objmodel.commitall)
        self.connect(ui.revertButton,    QtCore.SIGNAL("clicked()"), param.params.objmodel.revertall)
        if param.params.applyOK:
            self.connect(ui.applyButton, QtCore.SIGNAL("clicked()"), param.params.objmodel.applyall)
        else:
            self.connect(ui.applyButton, QtCore.SIGNAL("clicked()"),
                         lambda : 
                         QtGui.QMessageBox.critical(None, "Error", 
                                                    "Apply disabled.  Restart with --apply-enable.",
                                                    QtGui.QMessageBox.Ok))
        self.connect(ui.actionAuto,      QtCore.SIGNAL("triggered()"), param.params.objmodel.doShow)
        self.connect(ui.actionProtected, QtCore.SIGNAL("triggered()"), param.params.objmodel.doShow)
        self.connect(ui.actionManual,    QtCore.SIGNAL("triggered()"), param.params.objmodel.doShow)
        self.connect(ui.actionTrack,     QtCore.SIGNAL("triggered()"), param.params.objmodel.doTrack)
        self.connect(ui.actionAuth, QtCore.SIGNAL("triggered()"), self.doAuthenticate)
        self.connect(ui.actionExit, QtCore.SIGNAL("triggered()"), self.doExit)
        self.connect(self.utimer, QtCore.SIGNAL("timeout()"), self.unauthenticate)
        self.connect(ui.objectTable.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection,QItemSelection)"),
                     param.params.objmodel.selectionChanged)
        # MCB - Sigh. I should just make FreezeTableView actually work.
        self.connect(ui.objectTable.cTV.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection,QItemSelection)"),
                     param.params.objmodel.selectionChanged)

    def closeEvent(self, event):
        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(param.params.table)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("cfgcol/default", param.params.ui.configTable.saveHeaderState())
        settings.setValue("objcol/default", param.params.ui.objectTable.saveHeaderState())
        settings.setValue("grpcol/default", param.params.ui.groupTable.saveHeaderState())
        settings.setValue("objsel", param.params.objmodel.getObjSel())
        QtGui.QMainWindow.closeEvent(self, event)

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
            QtGui.QMessageBox.critical(None, "Error", "Invalid Password",
                                       QtGui.QMessageBox.Ok)
            return False

    def doAuthenticate(self):
        result = self.authdialog.exec_()
        user = str(self.authdialog.ui.nameEdit.text())
        password = str(self.authdialog.ui.passEdit.text())
        self.authdialog.ui.passEdit.setText("")
        if result == QtGui.QDialog.Accepted:
            if not self.authenticate_user(user, password):
                self.unauthenticate()

    def unauthenticate(self):
        self.utimer.stop()
        self.authenticate_user()
        
if __name__ == '__main__':
    QtGui.QApplication.setGraphicsSystem("raster")
    param.params = param.param_structure()
    app = QtGui.QApplication([''])
  
    # Options( [mandatory list, optional list, switches list] )
    options = Options(['hutch', 'type'], [], ['debug', 'apply-enabled'])
    try:
        options.parse()
    except Exception, msg:
        options.usage(str(msg))
        sys.exit()

    param.params.setHutch(options.hutch.lower())
    param.params.setTable(options.type)
    param.params.debug = False if options.debug == None else True
    param.params.applyOK = False if options.debug == None else True
    gui = GraphicUserInterface()
    try:
        gui.show()
        retval = app.exec_()
    except KeyboardInterrupt:
        app.exit(1)
    sys.exit(retval)
