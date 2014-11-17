import MySQLdb as mdb
import _mysql_exceptions
from PyQt4 import QtCore, QtGui
import threading
import datetime
import time
import re
import utils
import dialogs
import param

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
    
    def __init__(self, sig, interval):
        super(dbPoll, self).__init__()
        try:
            self.con = mdb.connect('psdb', 'pscontrols', 'pcds', 'pscontrols');
            cur = self.con.cursor(mdb.cursors.DictCursor)
            cur.execute("call init_pcds()")
        except:
            pass
        self.sig = sig
        self.interval = interval
        self.daemon = True
        self.do_db = True

    def run(self):
        last = 0
        lastcfg = datetime.datetime(1900,1,1,0,0,1)
        lastobj = datetime.datetime(1900,1,1,0,0,1)
        first = True
        cur = self.con.cursor(mdb.cursors.DictCursor)
        while True:
            now = time.time()
            looptime = now - last
            if looptime < self.interval:
                time.sleep(self.interval + 1 - looptime)
                last = time.time()
            else:
                last = now
            if not self.do_db:
                continue
            cur.execute("select * from ims_motor_update where tbl_name = 'config' or tbl_name = %s",
                        (param.params.hutch,))
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

    def start_transaction(self):
        self.do_db = False

    def end_transaction(self):
        self.do_db = True

class db(QtCore.QObject):
    cfgchange     = QtCore.pyqtSignal()
    objchange     = QtCore.pyqtSignal()
    readsig       = QtCore.pyqtSignal(int)

    def __init__(self):
        super(db, self).__init__()
        self.cfgs = None
        self.objs = None
        self.initsig = None
        self.errorlist = []
        self.cfgmap = {}
        self.in_trans = False
        self.nameedits = {}
        self.cur = None
        self.errordialog = dialogs.errordialog()
        try:
            self.con = mdb.connect('psdb', 'pscontrols', 'pcds', 'pscontrols');
            self.cur = self.con.cursor(mdb.cursors.DictCursor)
            self.cur.execute("call init_pcds()")
        except:
            pass
        self.readFormat()
        self.readsig.connect(self.readTables)
        self.poll = dbPoll(self.readsig, 30)
        self.con.commit()

    def start(self, initsig):
        self.initsig = initsig
        self.poll.start()

    def readFormat(self):
        self.cur.execute("describe %s" % param.params.table)
        locfld = [(d['Field'], m2pType(d['Type'])) for d in self.cur.fetchall()]
        locfld = locfld[7:]   # Skip the standard fields!

        self.cur.execute("describe %s_cfg" % param.params.table)
        fld = [(d['Field'], m2pType(d['Type'])) for d in self.cur.fetchall()]
        fld = fld[6:]         # Skip the standard fields!
        self.cfgfldcnt = len(fld)
        self.objfldcnt = len(locfld) + self.cfgfldcnt

        self.cur.execute("select * from %s_name_map" % param.params.table)
        result = self.cur.fetchall()
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
        
    def readDB(self, is_hutch):
        if is_hutch:
            ext = " where owner = '%s'" % param.params.hutch
        else:
            ext = "_cfg"
        self.cur.execute("select * from %s%s" % (param.params.table, ext))
        return list(self.cur.fetchall())

    def setObjNames(self):
        for o in self.objs.values():
            o['cfgname'] = self.getCfgName(o['config'])

    def readTables(self, mask=dbPoll.CONFIG|dbPoll.OBJECT, nosig=False):
        if self.in_trans:                       # This shouldn't happen.  But let's be paranoid.
            return
        if (mask & dbPoll.CONFIG) != 0:
            cfgs = self.readDB(False)
            map = {}
            for d in cfgs:
                map[d['id']] = d
            self.cfgs = map
            for d in cfgs:
                r = d['config']
                if r == None:
                    d['cfgname'] = ""
                else:
                    d['cfgname'] = self.getCfgName(r)
        if (mask & dbPoll.OBJECT) != 0:
            objs = self.readDB(True)
            objmap = {}
            for o in objs:
                objmap[o['id']] = o
            self.objs = objmap
            if self.initsig == None:
                self.setObjNames()
        if not nosig:
            self.con.commit()
            if (mask & dbPoll.CONFIG) != 0:
                self.cfgchange.emit()
            if (mask & dbPoll.OBJECT) != 0:
                self.objchange.emit()
        if self.initsig != None and self.cfgs != None and self.objs != None:
            self.setObjNames()
            self.initsig.emit()
            self.initsig = None;

    def getCfgName(self, id):
        try:
            return self.nameedits[id]
        except:
            return self.cfgs[id]['name']

    def setCfgName(self, id, name):
        try:
            if self.cfgs[id]['name'] == name:
                del self.cfgs[id]['name']
            else:
                self.nameedits[id] = name
        except:
            self.nameedits[id] = name

    def start_transaction(self):
        self.in_trans = True
        self.poll.start_transaction()
        self.errorlist = []
        self.cfgmap = {}
        try:
            self.cur.execute("lock tables %s write, %s_cfg write" % (param.params.table, param.params.table))
            self.readTables(dbPoll.CONFIG|dbPoll.OBJECT, True)
            return True
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            self.end_transaction()
            return False

    def transaction_error(self, msg):
        self.errorlist.append(_mysql_exceptions.Error(0, msg))

    def end_transaction(self):
        if self.errorlist != []:
            self.con.rollback()
        else:
            self.con.commit()
        try:
            self.cur.execute("unlock tables")
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
        self.in_trans = False
        self.poll.end_transaction()
        self.readTables()
        if self.errorlist:
            w = self.errordialog.ui.errorText
            w.setPlainText("")
            for e in self.errorlist:
                (n, m) = e.args
                if n != 0:
                    w.appendPlainText("Error %d: %s\n" % (n, m))
                else:
                    w.appendPlainText("Error: %s\n" % (m))
            self.errordialog.exec_()
            return False
        else:
            return True

    def configDelete(self, idx):
        try:
            if self.cur.execute("select id from %s where config = %%s" % param.params.table, (idx,)) != 0:
                self.errorlist.append(
                    _mysql_exceptions.Error(0,
                                            "Can't delete configuration %s, still in use." % self.getCfgName(idx)))
                                                              
                return
            self.cur.execute("delete from %s_cfg where id = %%s" % param.params.table, (idx,))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
 
    #
    # Security?
    #
    def configInsert(self, d):
        cmd = "insert %s_cfg (name, config, owner, dt_updated" % param.params.table
        vals = d['_val']
        for f in self.cfgflds:
            fld = f['fld']
            if vals[fld]:
                cmd += ", " + fld
        cmd += ") values (%s, %s, %s, now()"
        vlist = [d['name']]
        try:
            vlist.append(self.cfgmap[d['config']])
        except:
            vlist.append(d['config'])
        vlist.append(param.params.hutch)
        for f in self.cfgflds:
            fld = f['fld']
            if vals[fld]:
                cmd += ", %s"
                vlist.append(d[fld])
        cmd += ')'
        print cmd
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            return
        try:
            self.cur.execute("select id from %s_cfg where name = %%s" % param.params.table, (d['name'],))
            result = self.cur.fetchone()
            self.cfgmap[d['id']] = result['id']
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            self.cfgmap[d['id']] = d['id']   # This is still mapping to a negative,
                                             # just so we can go a little further.
            
    def configChange(self, d, e, ev):
        idx = d['id']
        cmd = "update %s_cfg set dt_updated = now()" % param.params.table
        vlist = []
        try:
            v = e['name']
            cmd += ", name = %s"
            vlist.append(v)
        except:
            pass
        try:
            v = e['config']
            cmd += ", config = %s"
            try:
                vlist.append(self.cfgmap[v])
            except:
                vlist.append(v)
        except:
            pass
        for f in self.cfgflds:
            fld = f['fld']
            try:
                v = e[fld]           # We have a new value!
            except:
                try:
                    if not ev[fld]:  # We want to inherit now!
                        v = None
                    else:          # We want to set the value to what we are inheriting!
                        v = d[fld]
                except:
                    continue       # No change to this field!
            cmd += ", %s = %%s" % fld
            vlist.append(v)
        cmd += ' where id = %s'
        vlist.append(idx)
        print cmd % tuple(vlist)
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as err:
            self.errorlist.append(err)

    def objectDelete(self, idx):
        try:
            self.cur.execute("delete from %s where id = %%s" % param.params.table, (idx,))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
        pass

    def objectInsert(self, d):
        cmd = "insert %s (name, config, owner, rec_base, dt_created, dt_updated" % param.params.table
        for f in self.objflds:
            if f['obj'] == False:
                continue
            fld = f['fld']
            cmd += ", " + fld
        cmd += ") values (%s, %s, %s, %s, now(), now()"
        vlist = [d['name']]
        try:
            vlist.append(self.cfgmap[d['config']])
        except:
            vlist.append(d['config'])
        vlist.append(param.params.hutch)
        vlist.append(d['rec_base'])
        for f in self.objflds:
            if f['obj'] == False:
                continue
            fld = f['fld']
            cmd += ", %s"
            vlist.append(d[fld])
        cmd += ')'
        print cmd
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)

    def objectChange(self, d, e):
        idx = d['id']
        cmd = "update %s set dt_updated = now()" % param.params.table
        vlist = []
        try:
            v = e['name']
            cmd += ", name = %s"
            vlist.append(v)
        except:
            pass
        try:
            v = e['config']
            cmd += ", config = %s"
            try:
                vlist.append(self.cfgmap[v])
            except:
                vlist.append(v)
        except:
            pass
        try:
            v = e['rec_base']
            cmd += ", rec_base = %s"
            vlist.append(v)
        except:
            pass
        for f in self.objflds:
            if f['obj'] == False:
                continue
            fld = f['fld']
            try:
                v = e[fld]           # We have a new value!
            except:
                continue
            cmd += "%s = %%s" % fld
            vlist.append(v)
        cmd += ' where id = %s'
        vlist.append(idx)
        print cmd % tuple(vlist)
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as err:
            self.errorlist.append(err)
