#!/usr/bin/env python
from PyQt4 import QtCore, QtGui
import sys
from psp.options import Options
from pmgr_ui import Ui_MainWindow
from ObjModel import ObjModel
from CfgModel import CfgModel
import param
import db
import threading

######################################################################
       
#
# Class to support for context menus in DropTableView.  The API is:
#     isActive(table, index)
#         - Return True is this menu should be displayed at this index
#           in the table.
#     doMenu(table, pos, index)
#         - Show/execute the menu at location pos/index in the table.
#     addAction(name, action)
#         - Create a menu item named "name" that, when selected, calls
#           action(table, index) to perform the action.
#
class MyContextMenu(QtGui.QMenu):
    def __init__(self, isActive=None):
        QtGui.QMenu.__init__(self)
        self.isActive = isActive
        self.actions = []

    def addAction(self, name, action):
        QtGui.QMenu.addAction(self, name)
        self.actions.append((name, action))

    def doMenu(self, table, pos, index):
        gpos = table.viewport().mapToGlobal(pos)
        selectedItem = self.exec_(gpos)
        if selectedItem != None:
            txt = selectedItem.text()
            for name, action in self.actions:
                if txt == name:
                    action(table, index)
                    return

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

        self.ui.configTable.verticalHeader().hide()
        self.ui.configTable.setCornerButtonEnabled(False)

        self.db = db.db(self.hutch, self.table)
        self.initdone.connect(self.finishinit)
        self.db.start(self.initdone)
        
        settings = QtCore.QSettings("SLAC", "ParamMgr");
        self.restoreGeometry(settings.value("geometry/%s" % self.table).toByteArray());
        self.restoreState(settings.value("windowState/%s" % self.table).toByteArray());

    def finishinit(self):
        self.ui.menuView.addAction(self.ui.objectWidget.toggleViewAction())
        self.ui.objectWidget.setWindowTitle(self.table + " objects")
        self.objectmodel = ObjModel(self.db, self.ui)
        self.ui.objectTable.init(self.objectmodel, 1, 1)
        self.ui.objectTable.setShowGrid(True)
        self.ui.objectTable.resizeColumnsToContents()
        self.ui.objectTable.setSortingEnabled(True)
        self.ui.objectTable.sortByColumn(0, QtCore.Qt.AscendingOrder)

        self.ui.menuView.addAction(self.ui.configWidget.toggleViewAction())
        self.ui.configWidget.setWindowTitle(self.table + " configurations")
        self.configmodel = CfgModel(self.db, self.ui)
        self.ui.configTable.init(self.configmodel, 1, 1)
        self.ui.configTable.setShowGrid(True)
        self.ui.configTable.resizeColumnsToContents()

        self.db.objchange.connect(self.objectmodel.objchange)
        self.db.cfgchange.connect(self.objectmodel.cfgchange)
        self.db.cfgchange.connect(self.configmodel.cfgchange)

    def closeEvent(self, event):
        settings = QtCore.QSettings("SLAC", "ParamMgr");
        settings.setValue("geometry/%s" % self.table, self.saveGeometry())
        settings.setValue("windowState/%s" % self.table, self.saveState())
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
