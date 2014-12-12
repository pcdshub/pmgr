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
        self.almond.name = "almond"
        self.white  = QtGui.QColor(255,255,255)
        self.white.name = "white"
        self.gray   = QtGui.QColor(237,233,227)
        self.gray.name = "gray"
        self.ltblue = QtGui.QColor(0,  255,255)
        self.ltblue.name = "ltblue"
        self.blue   = QtGui.QColor(QtCore.Qt.blue)
        self.blue.name = "blue"
        self.red    = QtGui.QColor(QtCore.Qt.red)
        self.red.name = "red"
        self.black  = QtGui.QColor(QtCore.Qt.black)
        self.black.name = "black"
        self.purple = QtGui.QColor(204, 0, 102)
        self.purple.name = "purple"
        self.cfgdialog       = None
        self.colusedialog    = None
        self.colsavedialog   = None
        self.deriveddialog   = None
        self.settings = ("SLAC", "ParamMgr")
        self.debug  = False

        self.ui = None
        self.objmodel = None
        self.cfgmodel = None
        self.db = None

        self.hutch = None
        self.table = None
