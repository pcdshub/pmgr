from PyQt4 import QtGui, QtCore

params = None

class param_structure(object):
    def __init__(self):
        self.almond = QtGui.QColor(255,235,205)
        self.gray   = QtGui.QColor(237,233,227)
        self.blue   = QtGui.QColor(QtCore.Qt.blue)
        self.red    = QtGui.QColor(QtCore.Qt.red)
        self.black  = QtGui.QColor(QtCore.Qt.black)
