import MySQLdb as mdb
import re

con = None

def init():
    global con
    con = mdb.connect('psdb', 'pscontrolsa', 'pcds', 'pscontrols');
    cur = con.cursor(mdb.cursors.DictCursor)
    cur.execute("call init_pcds()")

def finish():
    global con
    if con:
        con.close()
        con = None

def getTables():
    global con
    cur = con.cursor(mdb.cursors.DictCursor)
    cur.execute("SHOW TABLES")
    n = cur.fetchall()
    return [nn.values()[0] for nn in n]


def getConfiguration(name, table):
    global con
    try:
        cur = con.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT id from %s where name = %%s" % table, (name))
        n = cur.fetchone().values()[0]
        cur.callproc("find_parents", (table, 3))
        d = {}
        for i in range(cur.rowcount):
            n = cur.fetchone()
            for k in n.keys():
                if n[k] == None:
                    del n[k]
            d.update(n)
        m = {}
        for k in d.keys():
            if k[:3] != "PV_" and k[:4] != "FLD_":
                del d[k]
            else:
                m[k] = fixName(k)
        return (d, m)
    except mdb.Error, e:
        print "Error %d: %s" % (e.args[0],e.args[1])
        return None
