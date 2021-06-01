# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pmgr.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(990, 608)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setMinimumSize(QtCore.QSize(0, 0))
        self.centralwidget.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.saveButton = QtWidgets.QPushButton(self.centralwidget)
        self.saveButton.setObjectName("saveButton")
        self.gridLayout.addWidget(self.saveButton, 0, 0, 1, 1)
        self.treeWidget = QtWidgets.QTreeWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setMinimumSize(QtCore.QSize(100, 0))
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.headerItem().setText(0, "1")
        self.treeWidget.header().setVisible(False)
        self.treeWidget.header().setStretchLastSection(True)
        self.gridLayout.addWidget(self.treeWidget, 1, 0, 1, 6)
        self.revertButton = QtWidgets.QPushButton(self.centralwidget)
        self.revertButton.setObjectName("revertButton")
        self.gridLayout.addWidget(self.revertButton, 0, 1, 1, 1)
        self.applyButton = QtWidgets.QPushButton(self.centralwidget)
        self.applyButton.setObjectName("applyButton")
        self.gridLayout.addWidget(self.applyButton, 0, 2, 1, 1)
        self.debugButton = QtWidgets.QPushButton(self.centralwidget)
        self.debugButton.setObjectName("debugButton")
        self.gridLayout.addWidget(self.debugButton, 0, 3, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 990, 20))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        self.menuFilter = QtWidgets.QMenu(self.menubar)
        self.menuFilter.setObjectName("menuFilter")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.objectWidget = QtWidgets.QDockWidget(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(6)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.objectWidget.sizePolicy().hasHeightForWidth())
        self.objectWidget.setSizePolicy(sizePolicy)
        self.objectWidget.setMinimumSize(QtCore.QSize(600, 100))
        self.objectWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.objectWidget.setObjectName("objectWidget")
        self.objectTable = FreezeTableView()
        self.objectTable.setObjectName("objectTable")
        self.objectWidget.setWidget(self.objectTable)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.objectWidget)
        self.configWidget = QtWidgets.QDockWidget(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(6)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.configWidget.sizePolicy().hasHeightForWidth())
        self.configWidget.setSizePolicy(sizePolicy)
        self.configWidget.setMinimumSize(QtCore.QSize(600, 100))
        self.configWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.configWidget.setObjectName("configWidget")
        self.configTable = FreezeTableView()
        self.configTable.setObjectName("configTable")
        self.userLabel = QtWidgets.QLabel(self.configTable)
        self.userLabel.setGeometry(QtCore.QRect(60, 220, 121, 16))
        self.userLabel.setObjectName("userLabel")
        self.configWidget.setWidget(self.configTable)
        MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea(2), self.configWidget)
        self.actionObjects = QtWidgets.QAction(MainWindow)
        self.actionObjects.setObjectName("actionObjects")
        self.actionConfigurations = QtWidgets.QAction(MainWindow)
        self.actionConfigurations.setObjectName("actionConfigurations")
        self.actionManual = QtWidgets.QAction(MainWindow)
        self.actionManual.setCheckable(True)
        self.actionManual.setChecked(True)
        self.actionManual.setObjectName("actionManual")
        self.actionProtected = QtWidgets.QAction(MainWindow)
        self.actionProtected.setCheckable(True)
        self.actionProtected.setChecked(False)
        self.actionProtected.setObjectName("actionProtected")
        self.actionTrack = QtWidgets.QAction(MainWindow)
        self.actionTrack.setCheckable(True)
        self.actionTrack.setObjectName("actionTrack")
        self.actionExit = QtWidgets.QAction(MainWindow)
        self.actionExit.setObjectName("actionExit")
        self.actionAuth = QtWidgets.QAction(MainWindow)
        self.actionAuth.setObjectName("actionAuth")
        self.menuFile.addAction(self.actionAuth)
        self.menuFile.addAction(self.actionExit)
        self.menuFilter.addAction(self.actionManual)
        self.menuFilter.addAction(self.actionProtected)
        self.menuFilter.addAction(self.actionTrack)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuFilter.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.saveButton.setText(_translate("MainWindow", "Save"))
        self.treeWidget.setToolTip(_translate("MainWindow", "Click to select a configuration to display in the Configurations window. \n"
"All ancestors and all children of the selected configuration will be displayed."))
        self.revertButton.setText(_translate("MainWindow", "Revert"))
        self.applyButton.setText(_translate("MainWindow", "Apply"))
        self.debugButton.setText(_translate("MainWindow", "Debug"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.menuFilter.setTitle(_translate("MainWindow", "Filter"))
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
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" background-color:#ffebcd;\">Almond BG</span> = Derived value</p></td></tr></table></body></html>"))
        self.objectWidget.setWindowTitle(_translate("MainWindow", "Objects"))
        self.configWidget.setToolTip(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<table border=\"0\" style=\"-qt-table-type: root; margin-top:4px; margin-bottom:4px; margin-left:4px; margin-right:4px;\">\n"
"<tr>\n"
"<td style=\"border: none;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Black   = Value is set in configuration.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" color:#ff0000;\">Red</span>     = Value is unsaved change.</p></td></tr></table></body></html>"))
        self.configWidget.setWindowTitle(_translate("MainWindow", "Configurations"))
        self.userLabel.setText(_translate("MainWindow", "User: Guest"))
        self.actionObjects.setText(_translate("MainWindow", "Objects"))
        self.actionConfigurations.setText(_translate("MainWindow", "Configurations"))
        self.actionManual.setText(_translate("MainWindow", "Show Manual"))
        self.actionProtected.setText(_translate("MainWindow", "Show Protected"))
        self.actionTrack.setText(_translate("MainWindow", "Track Object Config"))
        self.actionExit.setText(_translate("MainWindow", "Exit"))
        self.actionAuth.setText(_translate("MainWindow", "Authenticate"))

from pmgr.FreezeTableView import FreezeTableView
