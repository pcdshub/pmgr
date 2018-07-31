# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'deriveddialog.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_deriveddialog(object):
    def setupUi(self, deriveddialog):
        deriveddialog.setObjectName("deriveddialog")
        deriveddialog.resize(296, 136)
        self.verticalLayout = QtWidgets.QVBoxLayout(deriveddialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(deriveddialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.groupBox = QtWidgets.QGroupBox(deriveddialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout.addWidget(self.groupBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(deriveddialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(deriveddialog)
        self.buttonBox.accepted.connect(deriveddialog.accept)
        self.buttonBox.rejected.connect(deriveddialog.reject)
        QtCore.QMetaObject.connectSlotsByName(deriveddialog)

    def retranslateUi(self, deriveddialog):
        _translate = QtCore.QCoreApplication.translate
        deriveddialog.setWindowTitle(_translate("deriveddialog", "Derived Quantity Selection"))
        self.label.setText(_translate("deriveddialog", "Please select which field is a derived quantity:"))
        self.groupBox.setTitle(_translate("deriveddialog", "Fields"))

