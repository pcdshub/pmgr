import MySQLdb as mdb
import re
import pyca
from psp.Pv import Pv
import utils
import time

#
# class cfgobj is an object that is to be configured (a motor, etc.)
# The fields are:
#     name     - The name of the object.
#     table    - The type of the object.
#     locfld   - An ordered list of local configuration variables and their python types.
#                These do *not* appear in a stored configuration!
#     config   - The index of the configuration (0 = The empty default configuration).
#     rec_base - The PV base name.
#     fld2pv   - A mapping from mysql fields to PV names.
#     curcfg   - A dictionary of the configuration field values.
#
class cfgobj(object):
    con = None

    def m2pType(self, name):
        if name[:7] == 'varchar' or name[:8] == 'datetime':
            return str
        if name[:3] == 'int' or name[:8] == 'smallint' or name[:7] == 'tinyint':
            return int
        if name[:6] == 'double':
            return float
        print "Unknown type %s" % name
        return str #?

    def fixName(self, name):
        name = re.sub("::", "_", re.sub("_", ":", name))
        if name[:3] == "PV:":
            return name[2:]
        else:
            c = name.rindex(':')
            return name[3:c] + '.' + name[c+1:]

    def __init__(self, hutch, table, name, *rec_base):
        self.hutch = hutch
        self.table = table
        self.name = name
        
        if cfgobj.con == None:
            try:
                cfgobj.con = mdb.connect('psdb', 'pscontrols', 'pcds', 'pscontrols');
                cur = cfgobj.con.cursor(mdb.cursors.DictCursor)
                cur.execute("call init_pcds()")
            except:
                pass

        cur = cfgobj.con.cursor(mdb.cursors.DictCursor)

        cur.execute("describe %s" % self.table)
        self.locfld = [(d['Field'], self.m2pType(d['Type'])) for d in cur.fetchall()]
        self.locfld = self.locfld[7:]   # Skip the standard fields!

        cur.execute("describe %s_tpl" % self.table)
        self.fld = [(d['Field'], self.m2pType(d['Type'])) for d in cur.fetchall()]
        self.fld = self.fld[4:]         # Skip the standard fields!

        cur.execute("SELECT * from %s where name = %%s" % (table), (name))
        if cur.rowcount == 0:
            # No record for this, make one!
            sql = "insert into %s values (0, 0, '%s', '%s', '%s', now(), now()" % (table, hutch, name, rec_base[0])
            for (f, t) in self.locfld:
                if issubclass(t, basestring):
                    sql += ", ''"
                else:
                    sql += ", 0"
            sql += ')'
            cur.execute(sql)
            cfgobj.con.commit()
            cur.execute("SELECT * from %s where name = %%s" % (table), (name))
        d = cur.fetchone()
        self.id       = d['id']
        self.rec_base = d['rec_base']
        if self.rec_base != rec_base[0]:
            print ("Warning: %s in table %s already defined with base %s (not %s)" %
                   (name, table, self.rec_base, rec_base[0]))

        self.curcfg = {}
        for k in d.keys():
            if k[:3] == 'PV_' or k[:4] == 'FLD_':
                self.curcfg[k] = d[k]
        self.setConfigId(d['config'])

        self.pv     = {}
        self.curval = {}
        for k in self.curcfg.keys():
            n = self.rec_base + self.fixName(k)
            self.pv[k] = utils.monitorPv(n, self.pv_handler)
            self.pv[k].fldname = k

    def pv_handler(self, pv, e):
        if e is None:
            self.curval[pv.fldname] = pv.value

    def setConfigId(self, cfg):
        self.config = cfg
        cur = cfgobj.con.cursor(mdb.cursors.DictCursor)
        cur.callproc("find_parents", (self.table + "_tpl", self.config))
        for i in range(cur.rowcount):
            n = cur.fetchone()
            for k in n.keys():
                if (k[:3] != "PV_" and k[:4] != "FLD_") or n[k] == None:
                    del n[k]
            self.curcfg.update(n)

    def setConfigName(self, cfg):
        cur = cfgobj.con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT id from %s_tpl where name = %%s" % (self.table), (cfg))
        if cur.rowcount == 0:
            return False
        d = cur.fetchone()
        self.setConfigId(d['id'])
        cur.execute("UPDATE %s set config = %%s, dt_updated = now() where id = %%s" % self.table,
                    (str(self.config), str(self.id)))
        cfgobj.con.commit()
        return True

    def saveAsNewConfig(self, cfg):
        cur = cfgobj.con.cursor(mdb.cursors.DictCursor)
        sql = "insert into %s_tpl values (0, '%s', null, 0" % (self.table, cfg)
        for (f, t) in self.fld:
            if issubclass(t, basestring):
                sql += ", '%s'" % self.curval[f]
            else:
                sql += ", %s" % str(self.curval[f])
        sql += ')'
        print sql
        cur.execute(sql)
        cfgobj.con.commit()

if __name__ == '__main__':
    x = cfgobj("xcs", "ims_motor", "DG3:IPM2 diode X",  "XCS:DG3:MMS:15")
    y = cfgobj("xcs", "ims_motor", "DG3:IPM2 diode Y",  "XCS:DG3:MMS:14")
    z = cfgobj("xcs", "ims_motor", "DG3:IPM2 target Y", "XCS:DG3:MMS:16")
    pyca.flush_io()
    time.sleep(60)
