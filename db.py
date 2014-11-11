import MySQLdb as mdb
from PyQt4 import QtCore, QtGui
import threading
import datetime
import time
import re
import utils

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
                        v = v | 1
                else:
                    if d['dt_updated'] != lastobj:
                        lastobj = d['dt_updated']
                        v = v | 2
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
        self.pvdict = {}
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

    def readTable(self, mask):
        cur = self.con.cursor(mdb.cursors.DictCursor)
        if (mask & 1) != 0:
            self.cfgs = self.readDB(False, cur)
            d_name = {}
            d_cfg = {}
            for d in self.cfgs:
                d_name[d['id']] = d['name']
                d_cfg[d['id']] = d
            d_name.update(self.nameedits)
            self.id2name = d_name
            self.id2cfg  = d_cfg
            for d in self.cfgs:
                d['status'] = ""
                r = d['link']
                if r == None:
                    d['linkname'] = ""
                else:
                    d['linkname'] = self.id2name[r]
        if (mask & 2) != 0:
            self.objs = self.readDB(True, cur)
            for o in self.objs:
                o['status'] = ""
                d = {}
                for f in self.objflds:
                    if f['obj']:
                        d[f['fld']] = o[f['fld']]
                o['origcfg'] = d
            if self.initsig == None:
                self.connectAllPVs()
        self.con.commit()
        if (mask & 1) != 0:
            self.cfgchange.emit()
        if (mask & 2) != 0:
            self.objchange.emit()
        if self.initsig != None and self.cfgs != None and self.objs != None:
            self.connectAllPVs()
            self.initsig.emit()
            self.initsig = None;

    def connectAllPVs(self):
        newpvdict = {}
        for d in self.objs:
            d['linkname'] = self.id2name[d['config']]
            base = d['rec_base']
            d['connstat'] = self.objfldcnt*[False]
            for ofld in self.objflds:
                n = base + ofld['pv']
                f = ofld['fld']
                try:
                    pv = self.pvdict[n]
                    d[f] = pv.value
                    d['connstat'][ofld['objidx']] = True
                    print d['connstat']
                    del self.pvdict[n]
                except:
                    pv = utils.monitorPv(n, self.pv_handler)
                    if ofld['type'] == str:
                        pv.set_string_enum(True)
                newpvdict[n] = pv
                pv.obj = d
                pv.fld = f
            if reduce(lambda a,b: a and b, d['connstat']):
                del d['connstat']
                d['status'] = "".join(sorted("C" + d['status']))
        for pv in self.pvdict.values():
            pv.disconnect()
        self.pvdict = newpvdict
        
    def setModel(self, model):
        self.model = model

    def pv_handler(self, pv, e):
        if e is None:
            pv.obj[pv.fld] = pv.value
            idx = self.fldmap[pv.fld]['objidx']
            try:
                pv.obj['connstat'][idx] = True
                if reduce(lambda a,b: a and b, pv.obj['connstat']):
                    del pv.obj['connstat']
                    pv.obj['status'] = "".join(sorted("C" + pv.obj['status']))
                    self.model.statchange(pv.obj['id'])
            except:
                pass
            if self.model:
                self.model.pvchange(pv.obj['id'], idx)
