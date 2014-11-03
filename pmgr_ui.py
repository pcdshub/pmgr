# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pmgr.ui'
#
# Created: Mon Nov  3 15:44:04 2014
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(880, 608)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.treeWidget = QtGui.QTreeWidget(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setMinimumSize(QtCore.QSize(100, 0))
        self.treeWidget.setObjectName(_fromUtf8("treeWidget"))
        self.treeWidget.headerItem().setText(0, _fromUtf8("1"))
        self.treeWidget.header().setVisible(False)
        self.treeWidget.header().setStretchLastSection(True)
        self.gridLayout.addWidget(self.treeWidget, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 880, 23))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        self.menuView = QtGui.QMenu(self.menubar)
        self.menuView.setObjectName(_fromUtf8("menuView"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.objectWidget = QtGui.QDockWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.objectWidget.sizePolicy().hasHeightForWidth())
        self.objectWidget.setSizePolicy(sizePolicy)
        self.objectWidget.setMinimumSize(QtCore.QSize(600, 100))
        self.objectWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.objectWidget.setObjectName(_fromUtf8("objectWidget"))
        self.objectTable = FreezeTableView()
        self.objectTable.setObjectName(_fromUtf8("objectTable"))
        self.objectWidget.setWidget(self.objectTable)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.objectWidget)
        self.configWidget = QtGui.QDockWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.configWidget.sizePolicy().hasHeightForWidth())
        self.configWidget.setSizePolicy(sizePolicy)
        self.configWidget.setMinimumSize(QtCore.QSize(600, 100))
        self.configWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.configWidget.setObjectName(_fromUtf8("configWidget"))
        self.configTable = FreezeTableView()
        self.configTable.setObjectName(_fromUtf8("configTable"))
        self.configWidget.setWidget(self.configTable)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.configWidget)
        self.actionObjects = QtGui.QAction(MainWindow)
        self.actionObjects.setObjectName(_fromUtf8("actionObjects"))
        self.actionConfigurations = QtGui.QAction(MainWindow)
        self.actionConfigurations.setObjectName(_fromUtf8("actionConfigurations"))
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.menuFile.setTitle(QtGui.QApplication.translate("MainWindow", "File", None, QtGui.QApplication.UnicodeUTF8))
        self.menuView.setTitle(QtGui.QApplication.translate("MainWindow", "View", None, QtGui.QApplication.UnicodeUTF8))
        self.objectWidget.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Objects", None, QtGui.QApplication.UnicodeUTF8))
        self.configWidget.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Configurations", None, QtGui.QApplication.UnicodeUTF8))
        self.actionObjects.setText(QtGui.QApplication.translate("MainWindow", "Objects", None, QtGui.QApplication.UnicodeUTF8))
        self.actionConfigurations.setText(QtGui.QApplication.translate("MainWindow", "Configurations", None, QtGui.QApplication.UnicodeUTF8))

from FreezeTableView import FreezeTableView
