from PyQt4 import QtCore, QtGui
import threading
import time
import dialogs
import param
from pmgrobj import pmgrobj

class dbPoll(threading.Thread):
    
    def __init__(self, sig, interval):
        super(dbPoll, self).__init__()
        self.sig = sig
        self.interval = interval
        self.daemon = True

    def run(self):
        last = 0
        while True:
            now = time.time()
            looptime = now - last
            if looptime < self.interval:
                time.sleep(self.interval + 1 - looptime)
                last = time.time()
            else:
                last = now
            v = param.params.pobj.checkForUpdate()
            if v != 0:
                self.sig.emit(v)

class db(QtCore.QObject):
    cfgchange     = QtCore.pyqtSignal()
    objchange     = QtCore.pyqtSignal()
    grpchange     = QtCore.pyqtSignal()
    readsig       = QtCore.pyqtSignal(int)
    cfgrenumber   = QtCore.pyqtSignal(int, int)

    def __init__(self):
        super(db, self).__init__()
        self.nameedits = {}
        self.errordialog = dialogs.errordialog()
        param.params.pobj = pmgrobj(param.params.table, param.params.hutch, param.params.debug)
        self.readTables()
        self.readsig.connect(self.readTables)
        self.poll = dbPoll(self.readsig, 30)
        self.poll.start()

    def setCfgName(self, id, name):
        try:
            if param.params.pobj.cfgs[id]['name'] == name:
                del self.nameedits[id]['name']
            else:
                self.nameedits[id] = name
        except:
            self.nameedits[id] = name

    def getCfgName(self, id):
        try:
            return self.nameedits[id]
        except:
            return param.params.pobj.cfgs[id]['name']

    def setCfgNames(self, l):
        for o in l:
            c = o['config']
            if c == None:
                o['cfgname'] = ""
            else:
                o['cfgname'] = self.getCfgName(c)

    def readTables(self, mask=None, nosig=False):
        if mask == None:
            mask=param.params.pobj.DB_ALL
        mask = param.params.pobj.updateTables(mask)
        if mask == 0:
            return
        if (mask & param.params.pobj.DB_CONFIG) != 0:
            self.setCfgNames(param.params.pobj.cfgs.values())
        if (mask & param.params.pobj.DB_OBJECT) != 0:
            for o in param.params.pobj.objs.values():             # ObjModel will update this, so save the originals!
                save = {}
                save.update(o)
                o['_val'] = save
            self.setCfgNames(param.params.pobj.objs.values())
        if not nosig:
            if (mask & param.params.pobj.DB_CONFIG) != 0:
                self.cfgchange.emit()
            if (mask & param.params.pobj.DB_OBJECT) != 0:
                self.objchange.emit()
            if (mask & param.params.pobj.DB_GROUP) != 0:
                self.grpchange.emit()

    def start_transaction(self):
        if not param.params.pobj.start_transaction():
            self.end_transaction()
            return False
        else:
            return True

    def end_transaction(self):
        errorlist = param.params.pobj.end_transaction()
        if errorlist != []:
            w = self.errordialog.ui.errorText
            w.setPlainText("")
            for e in errorlist:
                w.appendPlainText(e)
            self.errordialog.exec_()
            return False
        else:
            self.readTables()
            return True

    def cfgrenumber(self, old, new):
        param.params.cfgmodel.cfgrenumber(old, new)
        param.params.objmodel.cfgrenumber(old, new)
        param.params.grpmodel.cfgrenumber(old, new)
