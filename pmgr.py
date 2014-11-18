#!/usr/bin/env python
from PyQt4 import QtCore, QtGui
import sys
from psp.options import Options
from pmgr_ui import Ui_MainWindow
from ObjModel import ObjModel
from CfgModel import CfgModel
import dialogs
import param
from db import db
import threading

######################################################################
                

class GraphicUserInterface(QtGui.QMainWindow):
    initdone = QtCore.pyqtSignal()

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        param.params.ui = Ui_MainWindow()
        param.params.ui.setupUi(self)
        self.setWindowTitle("Parameter Manager for %s (%s)" % (param.params.hutch.upper(), param.params.table))

        param.params.ui.objectTable.verticalHeader().hide()
        param.params.ui.objectTable.setCornerButtonEnabled(False)
        param.params.ui.objectTable.horizontalHeader().setMovable(True)

        param.params.ui.configTable.verticalHeader().hide()
        param.params.ui.configTable.setCornerButtonEnabled(False)
        param.params.ui.configTable.horizontalHeader().setMovable(True)

        param.params.db = db()
        self.initdone.connect(self.finishinit)
        param.params.db.start(self.initdone)

    def finishinit(self):
        param.params.ui.menuView.addAction(param.params.ui.configWidget.toggleViewAction())
        param.params.ui.configWidget.setWindowTitle(param.params.table + " configurations")
        param.params.cfgmodel = CfgModel()
        param.params.ui.configTable.init(param.params.cfgmodel, 0, 2)
        param.params.ui.configTable.setShowGrid(True)
        param.params.ui.configTable.resizeColumnsToContents()

        param.params.ui.menuView.addAction(param.params.ui.objectWidget.toggleViewAction())
        param.params.ui.objectWidget.setWindowTitle(param.params.table + " objects")
        param.params.objmodel = ObjModel()
        param.params.ui.objectTable.init(param.params.objmodel, 0, 2)
        param.params.ui.objectTable.setShowGrid(True)
        param.params.ui.objectTable.resizeColumnsToContents()
        param.params.ui.objectTable.setSortingEnabled(True)
        param.params.ui.objectTable.sortByColumn(param.params.objmodel.namecol, QtCore.Qt.AscendingOrder)

        param.params.objmodel.setupContextMenus(param.params.ui.objectTable)
        param.params.cfgmodel.setupContextMenus(param.params.ui.configTable)

        param.params.cfgdialog       = dialogs.cfgdialog(param.params.cfgmodel, self)
        param.params.colsavedialog   = dialogs.colsavedialog(self)
        param.params.colusedialog    = dialogs.colusedialog(self)

        param.params.db.objchange.connect(param.params.objmodel.objchange)
        param.params.db.cfgchange.connect(param.params.objmodel.cfgchange)
        param.params.db.cfgchange.connect(param.params.cfgmodel.cfgchange)

        param.params.cfgmodel.newname.connect(param.params.cfgmodel.haveNewName)
        param.params.cfgmodel.newname.connect(param.params.objmodel.haveNewName)
        param.params.cfgmodel.cfgChanged.connect(param.params.objmodel.cfgEdit)

        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(param.params.table)
        self.restoreGeometry(settings.value("geometry").toByteArray())
        self.restoreState(settings.value("windowState").toByteArray())
        param.params.ui.configTable.restoreHeaderState(settings.value("cfgcol/default").toByteArray())
        param.params.ui.objectTable.restoreHeaderState(settings.value("objcol/default").toByteArray())

        # MCB - Sigh.  I don't know why this is needed, but it is.
        h = param.params.ui.configTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)
        h = param.params.ui.objectTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)

        param.params.ui.configTable.colmgr = "%s/cfgcol" % param.params.table
        param.params.ui.objectTable.colmgr = "%s/objcol" % param.params.table

        self.connect(param.params.ui.saveButton, QtCore.SIGNAL("clicked()"), param.params.objmodel.commitall)
        self.connect(param.params.ui.applyButton, QtCore.SIGNAL("clicked()"), param.params.objmodel.applyall)

    def closeEvent(self, event):
        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(param.params.table)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("cfgcol/default", param.params.ui.configTable.saveHeaderState())
        settings.setValue("objcol/default", param.params.ui.objectTable.saveHeaderState())
        QtGui.QMainWindow.closeEvent(self, event)

if __name__ == '__main__':
    QtGui.QApplication.setGraphicsSystem("raster")
    param.params = param.param_structure()
    app = QtGui.QApplication([''])
  
    # Options( [mandatory list, optional list, switches list] )
    options = Options(['hutch', 'type'], [], ['debug'])
    try:
        options.parse()
    except Exception, msg:
        options.usage(str(msg))
        sys.exit()

    param.params.hutch = options.hutch.lower()
    param.params.table = options.type
    param.params.debug = False if options.debug == None else True
    gui = GraphicUserInterface()
    try:
        gui.show()
        retval = app.exec_()
    except KeyboardInterrupt:
        app.exit(1)
    sys.exit(retval)
