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

        cur.execute("describe %s_tpl" % self.table)
        fld = [(d['Field'], m2pType(d['Type'])) for d in cur.fetchall()]
        fld = fld[4:]         # Skip the standard fields!
        self.cfgfldcnt = len(fld)
        self.objfldcnt = len(locfld) + self.cfgfldcnt

        cur.execute("select * from %s_name_map" % self.table)
        result = cur.fetchall()
        alias = {}
        dorder = {}
        for d in result:
            f = d['db_field_name']
            alias[f] = d['alias']
            dorder[f] = d['displayorder']

        if len(dorder.values()) > 0:
            deforder = max(dorder.values()) + 1
        else:
            deforder = 1

        self.objflds = []
        self.fld2pv = {}
        self.pv2fld = {}
        
        for (f, t) in locfld:
            n = fixName(f)
            self.fld2pv[f] = n
            self.pv2fld[n] = f
            if f in alias.keys():
                self.objflds.append({'fld': f, 'pv': n, 'alias' : alias[f], 'dorder': dorder[f], 'type': t, 'obj': True})
            else:
                self.objflds.append({'fld': f, 'pv': n, 'alias' : f, 'dorder': deforder, 'type': t, 'obj': True})
        for (f, t) in fld:
            n = fixName(f)
            self.fld2pv[f] = n
            self.pv2fld[n] = f
            if f in alias.keys():
                self.objflds.append({'fld': f, 'pv': n, 'alias' : alias[f], 'dorder': dorder[f], 'type': t, 'obj': False})
            else:
                self.objflds.append({'fld': f, 'pv': n, 'alias' : f, 'dorder': deforder, 'type': t, 'obj': False})
        self.objflds.sort(key=lambda d: (d['dorder'], d['alias']))
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
            ext = " where hutch = '%s'" % self.hutch
        else:
            name = "config"
            ext = "_tpl"
        cur.execute("select * from %s%s" % (self.table, ext))
        return list(cur.fetchall())

    def buildmaps(self, dlist):
        d_id = {}
        d_name = {}
        for d in dlist:
            d_id[d['id']] = d
            d_name[d['name']] = d
        return (d_id, d_name)

    def readTable(self, mask):
        cur = self.con.cursor(mdb.cursors.DictCursor)
        if (mask & 1) != 0:
            self.cfgs = self.readDB(False, cur)
            (self.id2cfg, self.cfg2id) = self.buildmaps(self.cfgs)
            for d in self.cfgs:
                r = d['link']
                if r == None:
                    d['linkname'] = ""
                else:
                    d['linkname'] = self.id2cfg[r]['name']
        if (mask & 2) != 0:
            self.objs = self.readDB(True, cur)
            (self.id2obj, self.obj2id) = self.buildmaps(self.objs)
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

    def getCfg(self, idx):
        d = self.id2cfg[idx]
        if not 'vfld' in d.keys():
            vfld = []
            if d['link'] != None:
                vals = self.getCfg(d['link'])
            for (k, v) in d.items():
                if k[:3] != 'PV_' and k[:4] != 'FLD_':
                    continue
                if v == None:
                    d[k] = vals[k]
                else:
                    vfld.append(k)
            d['vfld'] = vfld
        return d

    def connectAllPVs(self):
        newpvdict = {}
        for d in self.objs:
            d['linkname'] = self.id2cfg[d['config']]['name']
            d['curval'] = {}
            base = d['rec_base']
            for ofld in self.objflds:
                n = base + ofld['pv']
                f = ofld['fld']
                try:
                    pv = self.pvdict[n]
                    d['curval'][f] = pv.value
                    del self.pvdict[n]
                except:
                    pv = utils.monitorPv(n, self.pv_handler)
                    if ofld['type'] == str:
                        pv.set_string_enum(True)
                newpvdict[n] = pv
                pv.obj = d
                pv.fld = f
        for pv in self.pvdict.values():
            pv.disconnect()
        self.pvdict = newpvdict
        
    def setModel(self, model):
        self.model = model

    def pv_handler(self, pv, e):
        if e is None:
            pv.obj['curval'][pv.fld] = pv.value
            if self.model:
                self.model.pvchange(pv.obj['id'], self.fldmap[pv.fld]['objidx'])
