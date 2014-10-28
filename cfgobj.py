import MySQLdb as mdb
import re

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
        if name[:3] == 'int':
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

    def __init__(self, name, table, *rec_base):
        self.name = name
        self.table = table
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
        self.locfld = self.locfld[6:]   # Skip the standard locfld!
        cur.execute("SELECT * from %s where name = %%s" % (table), (name))
        if cur.rowcount == 0:
            # No record for this, make one!
            sql = "insert into %s values (0, 0, '%s', '%s', now(), now()" % (table, name, rec_base[0])
            for (f, t) in self.locfld:
                print f
                print t
                if issubclass(t, basestring):
                    sql += ", ''"
                else:
                    sql += ", 0"
            sql += ')'
            print sql
            cur.execute(sql)
            cfgobj.con.commit()
            cur.execute("SELECT * from %s where name = %%s" % (table), (name))
        d = cur.fetchone()
        self.rec_base = d['rec_base']
        if self.rec_base != rec_base[0]:
            print ("Warning: %s in table %s already defined with base %s (not %s)" %
                   (name, table, self.rec_base, rec_base[0]))

        self.curcfg = {}
        for k in d.keys():
            if k[:3] == 'PV_' or k[:4] == 'FLD_':
                self.curcfg[k] = d[k]

        self.setConfig(d['config'])

        self.fld2pv = {}
        for k in self.curcfg.keys():
            if k[:3] != "PV_" and k[:4] != "FLD_":
                del self.curcfg[k]
            else:
                self.fld2pv[k] = self.fixName(k)

    def setConfig(self, cfg):
        self.config = cfg
        
        cur.callproc("find_parents", (self.table + "_tpl", self.config))
        for i in range(cur.rowcount):
            n = cur.fetchone()
            for k in n.keys():
                if n[k] == None:
                    del n[k]
            self.curcfg.update(n)
