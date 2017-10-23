# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pmgr.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(990, 608)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setMinimumSize(QtCore.QSize(0, 0))
        self.centralwidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.saveButton = QtGui.QPushButton(self.centralwidget)
        self.saveButton.setObjectName(_fromUtf8("saveButton"))
        self.gridLayout.addWidget(self.saveButton, 0, 0, 1, 1)
        self.applyButton = QtGui.QPushButton(self.centralwidget)
        self.applyButton.setObjectName(_fromUtf8("applyButton"))
        self.gridLayout.addWidget(self.applyButton, 0, 1, 1, 1)
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
        self.gridLayout.addWidget(self.treeWidget, 1, 0, 1, 5)
        self.debugButton = QtGui.QPushButton(self.centralwidget)
        self.debugButton.setObjectName(_fromUtf8("debugButton"))
        self.gridLayout.addWidget(self.debugButton, 0, 3, 1, 1)
        self.revertButton = QtGui.QPushButton(self.centralwidget)
        self.revertButton.setObjectName(_fromUtf8("revertButton"))
        self.gridLayout.addWidget(self.revertButton, 0, 2, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 990, 20))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        self.menuView = QtGui.QMenu(self.menubar)
        self.menuView.setObjectName(_fromUtf8("menuView"))
        self.menuFilter = QtGui.QMenu(self.menubar)
        self.menuFilter.setObjectName(_fromUtf8("menuFilter"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.objectWidget = QtGui.QDockWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(6)
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
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(6)
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
        self.groupWidget = QtGui.QDockWidget(MainWindow)
        self.groupWidget.setEnabled(True)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(6)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupWidget.sizePolicy().hasHeightForWidth())
        self.groupWidget.setSizePolicy(sizePolicy)
        self.groupWidget.setMinimumSize(QtCore.QSize(600, 116))
        self.groupWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.groupWidget.setObjectName(_fromUtf8("groupWidget"))
        self.groupTable = FreezeTableView()
        self.groupTable.setObjectName(_fromUtf8("groupTable"))
        self.userLabel = QtGui.QLabel(self.groupTable)
        self.userLabel.setGeometry(QtCore.QRect(70, 50, 121, 16))
        self.userLabel.setObjectName(_fromUtf8("userLabel"))
        self.groupWidget.setWidget(self.groupTable)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.groupWidget)
        self.actionObjects = QtGui.QAction(MainWindow)
        self.actionObjects.setObjectName(_fromUtf8("actionObjects"))
        self.actionConfigurations = QtGui.QAction(MainWindow)
        self.actionConfigurations.setObjectName(_fromUtf8("actionConfigurations"))
        self.actionAuto = QtGui.QAction(MainWindow)
        self.actionAuto.setCheckable(True)
        self.actionAuto.setChecked(True)
        self.actionAuto.setObjectName(_fromUtf8("actionAuto"))
        self.actionManual = QtGui.QAction(MainWindow)
        self.actionManual.setCheckable(True)
        self.actionManual.setChecked(True)
        self.actionManual.setObjectName(_fromUtf8("actionManual"))
        self.actionProtected = QtGui.QAction(MainWindow)
        self.actionProtected.setCheckable(True)
        self.actionProtected.setChecked(True)
        self.actionProtected.setObjectName(_fromUtf8("actionProtected"))
        self.actionTrack = QtGui.QAction(MainWindow)
        self.actionTrack.setCheckable(True)
        self.actionTrack.setObjectName(_fromUtf8("actionTrack"))
        self.actionExit = QtGui.QAction(MainWindow)
        self.actionExit.setObjectName(_fromUtf8("actionExit"))
        self.actionAuth = QtGui.QAction(MainWindow)
        self.actionAuth.setObjectName(_fromUtf8("actionAuth"))
        self.menuFile.addAction(self.actionAuth)
        self.menuFile.addAction(self.actionExit)
        self.menuFilter.addAction(self.actionAuto)
        self.menuFilter.addAction(self.actionManual)
        self.menuFilter.addAction(self.actionProtected)
        self.menuFilter.addAction(self.actionTrack)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuFilter.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.saveButton.setText(_translate("MainWindow", "Save", None))
        self.applyButton.setText(_translate("MainWindow", "Apply", None))
        self.treeWidget.setToolTip(_translate("MainWindow", "Click to select a configuration to display in the Configurations window. \n"
"All ancestors and all children of the selected configuration will be displayed.", None))
        self.debugButton.setText(_translate("MainWindow", "Debug", None))
        self.revertButton.setText(_translate("MainWindow", "Revert", None))
        self.menuFile.setTitle(_translate("MainWindow", "File", None))
        self.menuView.setTitle(_translate("MainWindow", "View", None))
        self.menuFilter.setTitle(_translate("MainWindow", "Filter", None))
        self.objectWidget.setToolTip(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<table border=\"0\" style=\"-qt-table-type: root; margin-top:4px; margin-bottom:4px; margin-left:4px; margin-right:4px;\">\n"
"<tr>\n"
"<td style=\"border: none;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Black = Value matches configuration.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#0000ff;\">Blue</span>   = Value differs from configuration (actual shown).</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ff0000;\">Red</span>    = Unsaved configuration change (new value shown).</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" background-color:#a0a0a0;\">Gray BG</span>     = Unconnected</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" background-color:#e0e0e0;\">Lt Gray BG</span>  = Configuration value (not editable!)</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" background-color:#ffebcd;\">Almond BG</span> = Derived value</p></td></tr></table></body></html>", None))
        self.objectWidget.setWindowTitle(_translate("MainWindow", "Objects", None))
        self.configWidget.setToolTip(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<table border=\"0\" style=\"-qt-table-type: root; margin-top:4px; margin-bottom:4px; margin-left:4px; margin-right:4px;\">\n"
"<tr>\n"
"<td style=\"border: none;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Black   = Value is set in configuration.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#0000ff;\">Blue</span>    = Value is inherited from unchanged parent configuration.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#cc0066;\">Purple</span> = Value is inherited from changed parent configuration.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ff0000;\">Red</span>     = Value is unsaved change.</p></td></tr></table></body></html>", None))
        self.configWidget.setWindowTitle(_translate("MainWindow", "Configurations", None))
        self.groupWidget.setToolTip(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<table border=\"0\" style=\"-qt-table-type: root; margin-top:4px; margin-bottom:4px; margin-left:4px; margin-right:4px;\">\n"
"<tr>\n"
"<td style=\"border: none;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Black = Value is set in database.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#0000ff;\">Blue  </span>= Value is in a new group.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ff0000;\">Red   </span>= Value is unsaved change.</p></td></tr></table></body></html>", None))
        self.groupWidget.setWindowTitle(_translate("MainWindow", "Cfg Groups", None))
        self.userLabel.setText(_translate("MainWindow", "User: Guest", None))
        self.actionObjects.setText(_translate("MainWindow", "Objects", None))
        self.actionConfigurations.setText(_translate("MainWindow", "Configurations", None))
        self.actionAuto.setText(_translate("MainWindow", "Show Auto", None))
        self.actionManual.setText(_translate("MainWindow", "Show Manual", None))
        self.actionProtected.setText(_translate("MainWindow", "Show Protected", None))
        self.actionTrack.setText(_translate("MainWindow", "Track Object Config", None))
        self.actionExit.setText(_translate("MainWindow", "Exit", None))
        self.actionAuth.setText(_translate("MainWindow", "Authenticate", None))

from FreezeTableView import FreezeTableView
