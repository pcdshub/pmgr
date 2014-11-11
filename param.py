from PyQt4 import QtGui, QtCore

params = None

def equal(v1, v2):
    if type(v1) == float:
        # I hate floating point.  OK, we need to be "close", but if we are *at* zero
        # the "close" test fails!
        return v1 == v2 or abs(v1 - v2) < (abs(v1) + abs(v2)) * 1e-12
    else:
        return v1 == v2

class param_structure(object):
    def __init__(self):
        self.almond = QtGui.QColor(255,235,205)
        self.gray   = QtGui.QColor(237,233,227)
        self.blue   = QtGui.QColor(QtCore.Qt.blue)
        self.red    = QtGui.QColor(QtCore.Qt.red)
        self.black  = QtGui.QColor(QtCore.Qt.black)
        self.purple = QtGui.QColor(204, 0, 102)
        self.cfgdialog       = None
        self.colusedialog    = None
        self.colsavedialog   = None
        self.settings = ("SLAC", "ParamMgr")
