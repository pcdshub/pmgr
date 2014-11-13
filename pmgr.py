#!/usr/bin/env python
from PyQt4 import QtCore, QtGui
import sys
from psp.options import Options
from pmgr_ui import Ui_MainWindow
from ObjModel import ObjModel
from CfgModel import CfgModel
import dialogs
import param
import db
import threading

######################################################################
                

class GraphicUserInterface(QtGui.QMainWindow):
    initdone = QtCore.pyqtSignal()

    def __init__(self, app, hutch, table):
        QtGui.QMainWindow.__init__(self)
        self.app = app
        self.hutch = hutch.lower()
        self.table = table
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Parameter Manager for %s (%s)" % (self.hutch.upper(), table))

        self.ui.objectTable.verticalHeader().hide()
        self.ui.objectTable.setCornerButtonEnabled(False)
        self.ui.objectTable.horizontalHeader().setMovable(True)

        self.ui.configTable.verticalHeader().hide()
        self.ui.configTable.setCornerButtonEnabled(False)
        self.ui.configTable.horizontalHeader().setMovable(True)

        self.db = db.db(self.hutch, self.table)
        self.initdone.connect(self.finishinit)
        self.db.start(self.initdone)

    def finishinit(self):
        self.ui.menuView.addAction(self.ui.configWidget.toggleViewAction())
        self.ui.configWidget.setWindowTitle(self.table + " configurations")
        self.configmodel = CfgModel(self.db, self.ui)
        self.ui.configTable.init(self.configmodel, 0, 2)
        self.ui.configTable.setShowGrid(True)
        self.ui.configTable.resizeColumnsToContents()

        self.ui.menuView.addAction(self.ui.objectWidget.toggleViewAction())
        self.ui.objectWidget.setWindowTitle(self.table + " objects")
        self.objectmodel = ObjModel(self.db, self.ui, self.configmodel)
        self.ui.objectTable.init(self.objectmodel, 0, 2)
        self.ui.objectTable.setShowGrid(True)
        self.ui.objectTable.resizeColumnsToContents()
        self.ui.objectTable.setSortingEnabled(True)
        self.ui.objectTable.sortByColumn(self.objectmodel.namecol, QtCore.Qt.AscendingOrder)

        self.objectmodel.setupContextMenus(self.ui.objectTable)
        self.configmodel.setupContextMenus(self.ui.configTable)

        param.params.cfgdialog       = dialogs.cfgdialog(self.configmodel, self)
        param.params.colsavedialog   = dialogs.colsavedialog(self)
        param.params.colusedialog    = dialogs.colusedialog(self)

        self.db.objchange.connect(self.objectmodel.objchange)
        self.db.cfgchange.connect(self.objectmodel.cfgchange)
        self.db.cfgchange.connect(self.configmodel.cfgchange)

        self.configmodel.newname.connect(self.configmodel.haveNewName)
        self.configmodel.newname.connect(self.objectmodel.haveNewName)
        self.configmodel.cfgChanged.connect(self.objectmodel.cfgEdit)

        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(self.table)
        self.restoreGeometry(settings.value("geometry").toByteArray())
        self.restoreState(settings.value("windowState").toByteArray())
        self.ui.configTable.restoreHeaderState(settings.value("cfgcol/default").toByteArray())
        self.ui.objectTable.restoreHeaderState(settings.value("objcol/default").toByteArray())

        # MCB - Sigh.  I don't know why this is needed, but it is.
        h = self.ui.configTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)
        h = self.ui.objectTable.horizontalHeader()
        h.resizeSection(1, h.sectionSize(1) + 1)

        self.ui.configTable.colmgr = "%s/cfgcol" % self.table
        self.ui.objectTable.colmgr = "%s/objcol" % self.table

        self.connect(self.ui.saveButton, QtCore.SIGNAL("clicked()"), self.objectmodel.commitall)
        self.connect(self.ui.applyButton, QtCore.SIGNAL("clicked()"), self.objectmodel.applyall)

    def closeEvent(self, event):
        settings = QtCore.QSettings(param.params.settings[0], param.params.settings[1])
        settings.beginGroup(self.table)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("cfgcol/default", self.ui.configTable.saveHeaderState())
        settings.setValue("objcol/default", self.ui.objectTable.saveHeaderState())
        QtGui.QMainWindow.closeEvent(self, event)

if __name__ == '__main__':
  QtGui.QApplication.setGraphicsSystem("raster")
  param.params = param.param_structure()
  app = QtGui.QApplication([''])
  
  # Options( [mandatory list, optional list, switches list] )
  options = Options(['hutch', 'type'],
                    [],
                    [])
  try:
    options.parse()
  except Exception, msg:
    options.usage(str(msg))
    sys.exit()

  gui = GraphicUserInterface(app, options.hutch, options.type)
  try:
      gui.show()
      retval = app.exec_()
  except KeyboardInterrupt:
      app.exit(1)
  sys.exit(retval)
