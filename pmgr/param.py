from PyQt5 import QtCore, QtGui
import pwd, os

AUTH_FILE = "/reg/g/pcds/pyps/config/%s/pmgr.auth"
params = None

def equal(v1, v2):
    try:
        if type(v1) == float:
            # I hate floating point.  OK, we need to be "close", but if we are *at* zero
            # the "close" test fails!
            return v1 == v2 or abs(v1 - v2) < (abs(v1) + abs(v2)) * 1e-12
        else:
            return v1 == v2
    except:
        return False

class param_structure(object):
    def __init__(self):
        self.myuid = pwd.getpwuid(os.getuid())[0]
        self.user = None
        self.almond = QtGui.QColor(255,235,205)
        self.almond.name = "almond"
        self.white  = QtGui.QColor(255,255,255)
        self.white.name = "white"
        self.gray   = QtGui.QColor(160,160,160)
        self.gray.name = "gray"
        self.ltgray = QtGui.QColor(224,224,224)
        self.ltgray.name = "ltgray"
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
        self.confirmdialog   = None
        self.settings = ("SLAC", "ParamMgr")
        self.debug  = False
        self.applyOK  = False

        self.ui = None
        self.objmodel = None
        self.cfgmodel = None
        self.db = None
        self.pobj = None

        self.hutch = None
        self.table = None

        self.PROTECTED = 0
        self.MANUAL    = 1
        self.AUTO      = 2
        self.catenum   = ["Protected", "Manual", "Auto"]    # Database names.
        self.setCatEnum(["Protected", "Manual"])    # Displayed names.

    def setCatEnum(self, l):
        self.catenum2 = l
        if self.ui != None:
            self.ui.actionProtected.setText("Show " + l[0])
            self.ui.actionManual.setText("Show " + l[1])

    def setTable(self, v):
        self.table = v
            
    def setHutch(self, v):
        self.hutch = v
        lines = open(AUTH_FILE % v).readlines()
        self.auth_users = [l.strip() for l in lines]
