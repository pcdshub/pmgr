# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'colchoose.ui'
#
# Created: Mon Nov 10 11:34:54 2014
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(285, 222)
        self.gridLayout_2 = QtGui.QGridLayout(Dialog)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.allButton = QtGui.QPushButton(Dialog)
        self.allButton.setObjectName(_fromUtf8("allButton"))
        self.gridLayout_2.addWidget(self.allButton, 0, 0, 1, 1)
        self.noneButton = QtGui.QPushButton(Dialog)
        self.noneButton.setObjectName(_fromUtf8("noneButton"))
        self.gridLayout_2.addWidget(self.noneButton, 0, 1, 1, 1)
        self.groupBox = QtGui.QGroupBox(Dialog)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.gridLayout_2.addWidget(self.groupBox, 1, 0, 1, 2)
        self.buttonBox = QtGui.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout_2.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Column Chooser", None, QtGui.QApplication.UnicodeUTF8))
        self.allButton.setText(QtGui.QApplication.translate("Dialog", "Select All", None, QtGui.QApplication.UnicodeUTF8))
        self.noneButton.setText(QtGui.QApplication.translate("Dialog", "Select None", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("Dialog", "Columns", None, QtGui.QApplication.UnicodeUTF8))

