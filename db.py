import MySQLdb as mdb
from PyQt4 import QtCore, QtGui
import threading
import datetime
import time
import re
import utils

#
# db is our main db class.  It uses a dbPoll to check for updates, and will
# read and notify the model classes when they are received.
#
# The Exported fields/methods are:
#     cfgfldcnt, cfgflds   - The count and a dictionary of configuration field information.
#     objfldcnt, objflds   - The count and a dictionary of object field information (a superset of
#                            configuration field information).
#     fldmap               - A field name to information dictionary mapping.
#     cfgs                 - The configurations, indexed by ID.
#     objs                 - The objects, indexed by ID.
#     getCfgName(id)       - Fetch the (possibly edited) configuration name.
#     setCfgName(id, name) - Set the configuration name, but do not commit it.
#

# Map MySQL types to python types in a quick and dirty manner.
def m2pType(name):
    if name[:7] == 'varchar' or name[:8] == 'datetime':
        return str
    if name[:3] == 'int' or name[:8] == 'smallint' or name[:7] == 'tinyint':
        return int
    if name[:6] == 'double':
        return float
    print "Unknown type %s" % name
    return str #?

# Map MySQL field names to PV extensions.
def fixName(name):
    name = re.sub("::", "_", re.sub("_", ":", name))
    if name[:3] == "PV:":
        return name[2:]
    else:
        c = name.rindex(':')
        return name[3:c] + '.' + name[c+1:]

def createAlias(name):
    name = re.sub("__", "_", name)
    if name[:3] == "PV_":
        return name[3:]
    if name[:4] == "FLD_":
        return name[4:]
    else:
        return name

class dbPoll(threading.Thread):
    CONFIG = 1
    OBJECT = 2
    
    def __init__(self, sig, interval, hutch):
        super(dbPoll, self).__init__()
        try:
            self.con = mdb.connect('psdb', 'pscontrols', 'pcds', 'pscontrols');
            cur = self.con.cursor(mdb.cursors.DictCursor)
            cur.execute("call init_pcds()")
        except:
            pass
        self.sig = sig
        self.interval = interval
        self.hutch = hutch
        self.daemon = True

    def run(self):
        last = 0
        lastcfg = datetime.datetime(1900,1,1,0,0,1)
        lastobj = datetime.datetime(1900,1,1,0,0,1)
        first = True
        while True:
            now = time.time()
            looptime = now - last
            if looptime < self.interval:
                time.sleep(self.interval + 1 - looptime)
                last = time.time()
            else:
                last = now
            cur = self.con.cursor(mdb.cursors.DictCursor)
            cur.execute("select * from ims_motor_update where tbl_name = 'config' or tbl_name = %s", self.hutch)
            v = 0
            for d in cur.fetchall():
                if d['tbl_name'] == 'config':
                    if d['dt_updated'] != lastcfg:
                        lastcfg = d['dt_updated']
                        v = v | self.CONFIG
                else:
                    if d['dt_updated'] != lastobj:
                        lastobj = d['dt_updated']
                        v = v | self.OBJECT
            if first:
                first = False
                v = 3
            if v != 0:
                self.sig.emit(v)
            self.con.commit()

class db(QtCore.QObject):
    cfgchange   = QtCore.pyqtSignal()
    objchange   = QtCore.pyqtSignal()
    readsig     = QtCore.pyqtSignal(int)

    def __init__(self, hutch, table):
        super(db, self).__init__()
        self.hutch = hutch
        self.table = table
        self.model = None
        self.cfgs = None
        self.objs = None
        self.initsig = None
        self.nameedits = {}
        try:
            self.con = mdb.connect('psdb', 'pscontrols', 'pcds', 'pscontrols');
            cur = self.con.cursor(mdb.cursors.DictCursor)
            cur.execute("call init_pcds()")
        except:
            pass
        self.readFormat()
        self.readsig.connect(self.readTable)
        self.poll = dbPoll(self.readsig, 30, hutch)
        self.con.commit()

    def start(self, initsig):
        self.initsig = initsig
        self.poll.start()

    def readFormat(self):
        cur = self.con.cursor(mdb.cursors.DictCursor)

        cur.execute("describe %s" % self.table)
        locfld = [(d['Field'], m2pType(d['Type'])) for d in cur.fetchall()]
        locfld = locfld[7:]   # Skip the standard fields!

        cur.execute("describe %s_cfg" % self.table)
        fld = [(d['Field'], m2pType(d['Type'])) for d in cur.fetchall()]
        fld = fld[6:]         # Skip the standard fields!
        self.cfgfldcnt = len(fld)
        self.objfldcnt = len(locfld) + self.cfgfldcnt

        cur.execute("select * from %s_name_map" % self.table)
        result = cur.fetchall()
        alias = {}
        for d in result:
            f = d['db_field_name']
            alias[f] = d['alias']

        self.objflds = []
        
        for (f, t) in locfld:
            n = fixName(f)
            if f in alias.keys():
                self.objflds.append({'fld': f, 'pv': n, 'alias' : alias[f], 'type': t, 'obj': True})
            else:
                self.objflds.append({'fld': f, 'pv': n, 'alias' : createAlias(f), 'type': t, 'obj': True})
        for (f, t) in fld:
            n = fixName(f)
            if f in alias.keys():
                self.objflds.append({'fld': f, 'pv': n, 'alias' : alias[f], 'type': t, 'obj': False})
            else:
                self.objflds.append({'fld': f, 'pv': n, 'alias' : createAlias(f), 'type': t, 'obj': False})
        self.objflds.sort(key=lambda d: (not d['obj'], d['alias']))
        self.fldmap = {}
        for i in range(len(self.objflds)):
            d = self.objflds[i]
            d['objidx'] = i
            self.fldmap[d['fld']] = d
        self.cfgflds = [d for d in self.objflds if d['obj'] == False]
        for i in range(len(self.cfgflds)):
            self.cfgflds[i]['cfgidx'] = i
        self.con.commit()
        
    def readDB(self, hutch, cur):
        if hutch:
            name = self.hutch
            ext = " where owner = '%s'" % self.hutch
        else:
            name = "config"
            ext = "_cfg"
        cur.execute("select * from %s%s" % (self.table, ext))
        return list(cur.fetchall())

    def getCfgName(self, id):
        try:
            return self.nameedits[id]
        except:
            return self.cfgs[id]['name']

    def setCfgName(self, id, name):
        if self.cfgs[id]['name'] == name:
            del self.cfgs[id]['name']
        else:
            self.nameedits[id] = name

    def setObjNames(self):
        for o in self.objs.values():
            o['cfgname'] = self.getCfgName(o['config'])

    def readTable(self, mask):
        cur = self.con.cursor(mdb.cursors.DictCursor)
        if (mask & dbPoll.CONFIG) != 0:
            cfgs = self.readDB(False, cur)
            cfgmap = {}
            for d in cfgs:
                cfgmap[d['id']] = d
                d['status'] = ""
            self.cfgs = cfgmap
            for d in cfgs:
                r = d['config']
                if r == None:
                    d['cfgname'] = ""
                else:
                    d['cfgname'] = self.getCfgName(r)
        if (mask & dbPoll.OBJECT) != 0:
            objs = self.readDB(True, cur)
            objmap = {}
            for o in objs:
                o['status'] = ""
                objmap[o['id']] = o
            self.objs = objmap
            if self.initsig == None:
                self.setObjNames()
        self.con.commit()
        if (mask & dbPoll.CONFIG) != 0:
            self.cfgchange.emit()
        if (mask & dbPoll.OBJECT) != 0:
            self.objchange.emit()
        if self.initsig != None and self.cfgs != None and self.objs != None:
            self.setObjNames()
            self.initsig.emit()
            self.initsig = None;
