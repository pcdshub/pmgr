import time
import datetime
import re

import MySQLdb as mdb
try:
    import _mysql_exceptions
except ImportError:
    import MySQLdb._exceptions as _mysql_exceptions
import pyca

from . import utils

####################
#
# Utility Functions
#
####################

# Map MySQL types to python types in a quick and dirty manner.
def m2pType(name):
    if name[:7] == 'varchar' or name[:8] == 'datetime':
        return str
    if name[:3] == 'int' or name[:8] == 'smallint' or name[:7] == 'tinyint':
        return int
    if name[:6] == 'double':
        return float
    print("Unknown type %s" % name)
    return None

# Map MySQL field names to PV extensions.
def fixName(name):
    name = re.sub("::", "_", re.sub("_", ":", name))
    if name[:3] == "PV:":
        return name[2:]
    else:
        c = name.rindex(':')
        return name[3:c] + '.' + name[c+1:]

# Map MySQL field names to the descriptive part of the name.
def createAlias(name):
    name = re.sub("__", "_", name)
    if name[:3] == "PV_":
        return name[3:]
    if name[:4] == "FLD_":
        return name[4:]
    else:
        return name

####################
#
# pmgrobj - The Parameter Manager Object class.
#
####################
#
# pmgrobj(table, hutch, debug=False)
#     - Create a parameter manager object to connect to the particular
#       database table for the particular hutch.  If debug is True,
#       no actual db operations will be performed, but mysql commands
#       will be printed.
#
# Exported fields:
#     objflds
#         - A list of dictionaries containing information about *all*
#           of the fields in this table, sorted by col_order.  Note that
#           col_order starts at one, so col_order - 1 should be used as
#           an index to this list.
#     cfgflds
#         - A list of dictionaries containing information about the
#           *configuration* fields in this table.  (This is a subset
#           of objflds.
#     mutex_sets
#         - A list of lists of field names in each mutual exclusion set.
#           (One of the fields in each list must be unset.)
#     mutex_obj
#         - A list of booleans for each mutual exclusion set indicating if
#           the set applies to an object (True) or a configuration (False).
#     mutex_flds
#         - A flat list of all of the field names in the mutex_sets.
#     fldmap
#         - A dictionary mapping field names to information dictionaries.
#     setflds
#         - A list containing lists of field names, each list having the
#           same setorder, with the entire list sorted by setorder.
#     cfgs
#         - A configuration ID to configuration dictionary mapping.
#           The keys are a few boilerplate keys (id, config, etc.)
#           and the configuration fields.  Note that due to inheritance
#           and mutual exclusion, many of these fields could be "None".
#     objs
#         - An object ID to object dictionary mapping.  The keys are a 
#           few boilerplate keys (id, config, etc.) and the object-only
#           fields (the objflds with the 'obj' key value True).
#
# The field information dictionaries have the following keys:
#     fld
#         - The field name.
#     pv
#         - The field name translated to a PV base extension.
#     alias
#         - A short alias for the field.
#     type
#         - A python type for the field (str, int, float, or None if
#           the type cannot be determined).
#     colorder
#         - The column display order (low numbers should come first).
#     setorder
#         - The PV setting order (low numbers should be set first).
#     mustwrite
#         - Must the PV value always be written, even if unchanged?
#     writezero
#         - Must the PV be cleared before a new value is written?
#     setmutex
#         - Is this PV part of a mutual exclusion set that cannot all
#           have values assigned?
#     mutex
#         - A list of mutex sets indices that this field is a member of.
#     obj
#         - Is this an object property, or a configuration property?
#     objidx
#         - The index of this field in objflds.
#     cfgidx
#         - The index of this field in cfgflds.
#     nullok
#         - Can this value be the empty string?
#     unique
#         - Must this field have a unique value?
#     tooltip
#         - The tooltip/hint text for this field.
#     readonly
#         - Is this field is readonly?
#
# Exported methods:
#     checkForUpdate()
#         - Returns a mask of DB_CONFIG and DB_OBJECT indicating
#           which tables (if any) are out of date.
#     updateTables(mask=DB_ALL)
#         - Read in the specified tables.
#     start_transaction()
#         - Begin to make DB changes.
#     transaction_error(msg)
#         - Generate an error message for the DB change.
#     end_transaction()
#         - Commit or rollback the current transaction.  Return a list of
#           error strings, so an empty list indicates a successful commit.
#     configDelete(idx, namefunc=None)
#         - Delete a configuration.  (namefunc is an idx -> name mapping function).
#     configInsert(d)
#         - Insert a new configuration.  Returns the new configuration ID or None
#           if it fails.
#     configChange(idx, e)
#         - Change an existing configuration.  e is a field -> value dictionary for
#           the changes.
#     objectDelete(idx)
#         - Delete an existing object.
#     objectInsert(d)
#         - Insert a new object.  Returns the new object ID or None if it fails.
#     objectChange(idx, e)
#         - Change an existing object.  e is a field -> value dictionary for the
#           changes.
#     countInstance(cfglist)
#         - Return a count of objects that depend on one of the listed configurations.
#     applyConfig(idx)
#         - Given an object ID, apply its current configuration to it.
#     applyAllConfigs()
#         - Apply the current configuration to all objects.
#     diffConfig(idx, cfgidx=None)
#         - Given an object ID and an optional configuration ID, return a dictionary from field
#           to (Actual_Value, Config_Value) that describes the difference between the configuration
#           and the PV settings.
#     getActualConfig(idx)
#         - Given an object ID, return a dictionary from configuration field to actual values.
#     matchConfigs(pattern, substr=False, ci=False)
#         - Return a list of configuration names that match the pattern, which may include
#           "*" to denote any string and "." to match any character. If ci is True, the 
#           match is case insensitive.  If substr is False, then the pattern must match
#           the entire string, otherwise it can match any substring.

class pmgrobj(object):
    DB_CONFIG = 1
    DB_OBJECT = 2
    DB_ALL    = 3

    ORDER_MASK    = 0x0003ff
    SETMUTEX_MASK = 0x000200
    MUST_WRITE    = 0x000400
    WRITE_ZERO    = 0x000800
    AUTO_CONFIG   = 0x001000
    READ_ONLY     = 0x002000

    unwanted = ['seq', 'owner', 'id', 'category', 'dt_created',
                'date', 'dt_updated', 'name', 'action', 'rec_base', 'comment']

    def __init__(self, table, hutch, debug=False):
        self.table = table
        self.hutch = hutch
        self.debug = debug
        self.cfgs = None
        self.objs = None
        self.errorlist = []
        self.autoconfig = None
        self.in_trans = False
        if False:
            print("Using production server.")
            self.con = mdb.connect('psdb', 'pscontrols', 'pcds', 'pscontrols')
        else:
            print("Using development server.")
            self.con = mdb.connect('psdbdev01', 'mctest', 'mctest', 'pscontrols')
        self.con.autocommit(False)
        self.cur = self.con.cursor(mdb.cursors.DictCursor)
        self.cur.execute("call init_pcds()")
        self.readFormat()
        self.dbgid = 42
        self.lastcfg = datetime.datetime(1900,1,1,0,0,1)
        self.lastobj = datetime.datetime(1900,1,1,0,0,1)
        self.hutchlist = self.getHutchList()
        self.checkForUpdate()
        self.updateTables()

    def readFormat(self):
        self.cur.execute("describe %s" % self.table)
        locfld = [(d['Field'], m2pType(d['Type']), d['Null'], d['Key']) for d in self.cur.fetchall()]

        self.cur.execute("describe %s_cfg" % self.table)
        fld = [(d['Field'], m2pType(d['Type']), d['Null'], d['Key']) for d in self.cur.fetchall()]

        self.cur.execute("select * from %s_name_map" % self.table)
        result = self.cur.fetchall()

        alias = {}
        colorder = {}
        setorder = {}
        tooltip = {}
        enum = {}
        mutex = {}
        nullok = {}
        unique = {}
        mutex_sets = []
        mutex_flds = []
        for i in range(16):
            mutex_sets.append([])
        for (f, t, nl, k) in locfld:
            if f[0].isupper():
                alias[f] = createAlias(f)
                colorder[f] = 1000
                setorder[f] = 0
                mutex[f] = 0
                tooltip[f] = ''
                nullok[f] = ((nl == 'YES') or (t != str))
                unique[f] = k == "UNI"
        for (f, t, nl, k) in fld:
            if f[0].isupper():
                alias[f] = createAlias(f)
                colorder[f] = 1000
                setorder[f] = 0
                mutex[f] = 0
                tooltip[f] = ''
                nullok[f] = ((nl == 'YES') or (t != str))
                unique[f] = k == "UNI"

        for d in result:
            f = d['db_field_name']
            if d['alias'] != "":
                alias[f] = d['alias']
            colorder[f] = d['col_order']
            setorder[f] = d['set_order']
            tooltip[f] = d['tooltip']
            v = d['enum']
            if v != "":
                enum[f] = v.split('|')
            v = d['mutex_mask']
            if v != 0:
                for i in range(16):
                    if v & (1 << i) != 0:
                        mutex_sets[i].append(f)
                mutex_flds.append(f)
            if setorder[f] & self.AUTO_CONFIG != 0:
                self.autoconfig = f
        # We're assuming the bits are used from LSB to MSB, no gaps!
        self.mutex_sets = [l for l in mutex_sets if l != []]
        self.mutex_flds = mutex_flds
        for d in result:
            f = d['db_field_name']
            mutex[f] = []
            v = d['mutex_mask']
            if v != 0:
                for i in range(16):
                    if v & (1 << i) != 0:
                        mutex[f].append(i)

        self.objflds = []
        setflds = {}
        setset = set([])
        for (f, t, nl, k) in locfld:
            if f[0].isupper():
                n = fixName(f)
                so = setorder[f] & self.ORDER_MASK
                setset.add(so)
                d = {'fld': f, 'pv': n, 'alias' : alias[f], 'type': t, 'nullok': nullok[f],
                     'colorder': colorder[f], 'setorder': so, 'unique': unique[f],
                     'mustwrite': (setorder[f] & self.MUST_WRITE) == self.MUST_WRITE,
                     'writezero': (setorder[f] & self.WRITE_ZERO) == self.WRITE_ZERO,
                     'setmutex': (setorder[f] & self.SETMUTEX_MASK) == self.SETMUTEX_MASK,
                     'readonly': (setorder[f] & self.READ_ONLY) == self.READ_ONLY,
                     'tooltip': tooltip[f], 'mutex' : mutex[f], 'obj': True}
                try:
                    setflds[so].append(f)
                except:
                    setflds[so] = [f]
                try:
                    d['enum'] = enum[f]
                except:
                    pass 
                self.objflds.append(d)
        for (f, t, nl, k) in fld:
            if f[0].isupper():
                n = fixName(f)
                so = setorder[f] & self.ORDER_MASK
                setset.add(so)
                d = {'fld': f, 'pv': n, 'alias' : alias[f], 'type': t, 'nullok': nullok[f],
                     'colorder': colorder[f], 'setorder': so, 'unique': unique[f],
                     'mustwrite': (setorder[f] & self.MUST_WRITE) == self.MUST_WRITE,
                     'writezero': (setorder[f] & self.WRITE_ZERO) == self.WRITE_ZERO,
                     'setmutex': (setorder[f] & self.SETMUTEX_MASK) == self.SETMUTEX_MASK,
                     'readonly': (setorder[f] & self.READ_ONLY) == self.READ_ONLY,
                     'tooltip': tooltip[f], 'mutex' : mutex[f], 'obj': False}
                try:
                    setflds[so].append(f)
                except:
                    setflds[so] = [f]
                try:
                    d['enum'] = enum[f]
                except:
                    pass
                self.objflds.append(d)
        self.objflds.sort(key=lambda d: d['colorder'])   # New regime: col_order is manditory and unique!
        self.fldmap = {}
        for i in range(len(self.objflds)):
            d = self.objflds[i]
            d['objidx'] = i
            self.fldmap[d['fld']] = d
        self.cfgflds = [d for d in self.objflds if d['obj'] == False]
        for i in range(len(self.cfgflds)):
            self.cfgflds[i]['cfgidx'] = i
        # Set the type of each mutex_set and make sure it's consistent
        self.mutex_obj = []
        for l in self.mutex_sets:
            self.mutex_obj.append(self.fldmap[l[0]]['obj'])
            for m in l:
                if self.fldmap[m]['obj'] != self.mutex_obj[-1]:
                    print("Inconsistent mutex set %s!" % str(l))
                    raise Exception()
        setset = list(setset)
        setset.sort()
        self.setflds = [setflds[i] for i in setset]
        self.con.commit()

    def getHutchList(self):
        l = []
        try:
            self.cur.execute("select * from %s_update" % (self.table))
            for d in self.cur.fetchall():
                n = d['tbl_name']
                if n != 'config':
                    l.append(n)
            self.con.commit()
            l.sort()
        except:
            pass
        return l

    def checkForUpdate(self):
        if self.in_trans:
            return 0      # Not now!
        try:
            v = 0
            if self.hutch is None:
                self.cur.execute("select * from %s_update" % self.table)
            else:
                self.cur.execute("select * from %s_update where tbl_name = 'config' or tbl_name = '%s'" %
                                 (self.table, self.hutch))
            for d in self.cur.fetchall():
                if d['tbl_name'] == 'config':
                    if d['dt_updated'] > self.lastcfg:
                        self.lastcfg = d['dt_updated']
                        v = v | self.DB_CONFIG
                else:
                    if d['dt_updated'] > self.lastobj:
                        self.lastobj = d['dt_updated']
                        v = v | self.DB_OBJECT
            self.con.commit()
        except:
            pass
        return v

    def readDB(self, kind):
        if kind == self.DB_CONFIG:
            ext = "_cfg"
        else: # self.DB_OBJECT
            if self.hutch is None:
                ext = ""
            else:
                ext = " where owner = '%s'" % self.hutch
        try:
            self.cur.execute("select * from %s%s" % (self.table, ext))
            return list(self.cur.fetchall())
        except:
            return []

    def updateTables(self, mask=DB_ALL):
        if self.in_trans:                    # This shouldn't happen.  But let's be paranoid.
            return
        if (mask & self.DB_CONFIG) != 0:
            cfgs = self.readDB(self.DB_CONFIG)
            if cfgs == []:
                mask &= ~self.DB_CONFIG
            else:
                map = {}
                for d in cfgs:
                    map[d['id']] = d
                self.cfgs = map
        if (mask & self.DB_OBJECT) != 0:
            objs = self.readDB(self.DB_OBJECT)
            if objs == []:
                mask &= ~self.DB_OBJECT
            else:
                objmap = {}
                for o in objs:
                    objmap[o['id']] = o
                self.objs = objmap
        return mask

    def start_transaction(self):
        self.in_trans = True
        self.errorlist = []
        return True

    def transaction_error(self, msg):
        self.errorlist.append(_mysql_exceptions.Error(0, msg))

    def end_transaction(self):
        didcommit = False
        if self.errorlist == []:
            try:
                self.con.commit()
                if self.debug:
                    print("COMMIT!")
                didcommit = True
            except _mysql_exceptions.Error as e:
                self.errorlist.append(e)
        if not didcommit:
            self.con.rollback()
            if self.debug:
                print("ROLLBACK!")
        self.in_trans = False
        el = []
        for e in self.errorlist:
            if len(e.args) == 1:
                n = e.args[0]
                m = ""
            else:
                (n, m) = e.args
            if n != 0:
                el.append("Error %d: %s\n" % (n, m))
            else:
                el.append("Error: %s\n" % (m))
        return el

####################
#
# Actual database manipulation routines!
#
####################

    @staticmethod
    def defaultNamefunc(idx):
        return "#" + str(idx)

    def configDelete(self, idx, namefunc=defaultNamefunc):
        try:
            if self.cur.execute("select id from %s where config = %%s" % self.table, (idx,)) != 0:
                self.errorlist.append(
                    _mysql_exceptions.Error(0,
                                            "Can't delete configuration %s, still in use." % namefunc(idx)))
                return
            self.cur.execute("delete from %s_cfg where id = %%s" % self.table, (idx,))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
 
    def configInsert(self, d):
        cmd = "insert %s_cfg (name, config, mutex, dt_updated" % self.table
        for f in self.cfgflds:
            fld = f['fld']
            cmd += ", " + fld
        cmd += ") values (%s, %s, %s, now()"
        vlist = [d['name']]
        vlist.append(d['config'])
        vlist.append(d['mutex'])
        for f in self.cfgflds:
            fld = f['fld']
            cmd += ", %s"
            vlist.append(d[fld])
        cmd += ')'
        if self.debug:
            print(cmd % tuple(vlist))
            id = self.dbgid
            self.dbgid += 1
            return id
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            return None
        try:
            self.cur.execute("select last_insert_id()")
            return list(self.cur.fetchone().values())[0]
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            return None
            
    def configChange(self, idx, e, update=True):
        cmd = "update %s_cfg set " % self.table
        if update:
            cmd += "dt_updated = now()"
            sep = ", "
        else:
            sep = ""
        vlist = []
        try:
            v = e['name']
            cmd += "%sname = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        try:
            v = e['config']
            cmd += "%sconfig = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        try:
            v = e['mutex']
            cmd += "%smutex = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        for f in self.cfgflds:
            fld = f['fld']
            try:
                v = e[fld]           # We have a new value!
                cmd += "%s%s = %%s" % (sep, fld)
                sep = ", "
                vlist.append(v)
            except:
                pass                 # No change to this field!
        cmd += ' where id = %s'
        vlist.append(idx)
        if self.debug:
            print(cmd % tuple(vlist))
            return
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as err:
            self.errorlist.append(err)

    def objectDelete(self, idx):
        try:
            self.cur.execute("delete from %s where id = %%s" % self.table, (idx,))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)

    def objectInsert(self, d):
        cmd = "insert %s (name, config, owner, rec_base, category, mutex, dt_created, dt_updated, comment" % self.table
        for f in self.objflds:
            if f['obj'] == False:
                continue
            fld = f['fld']
            cmd += ", " + fld
        cmd += ") values (%s, %s, %s, %s, %s, %s, now(), now(), %s"
        vlist = [d['name']]
        vlist.append(d['config'])
        vlist.append(self.hutch)
        vlist.append(d['rec_base'])
        vlist.append(d['category'])
        vlist.append(d['mutex'])
        vlist.append(d['comment'])
        for f in self.objflds:
            if f['obj'] == False:
                continue
            fld = f['fld']
            cmd += ", %s"
            vlist.append(d[fld])
        cmd += ')'
        if self.debug:
            print(cmd % tuple(vlist))
            id = self.dbgid
            self.dbgid += 1
            return id
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
        try:
            self.cur.execute("select last_insert_id()")
            return list(self.cur.fetchone().values())[0]
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            return None

    def objectChange(self, idx, e, update=True):
        cmd = "update %s set " % self.table
        if update:
            cmd += "dt_updated = now()"
            sep = ", "
        else:
            sep = ""
        vlist = []
        try:
            v = e['name']
            cmd += "%sname = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        try:
            v = e['config']
            cmd += "%sconfig = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        try:
            v = e['rec_base']
            cmd += "%srec_base = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        try:
            v = e['category']
            cmd += "%scategory = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        try:
            v = e['mutex']
            cmd += "%smutex = %%s" % sep
            sep = ", "
            vlist.append(v)
        except:
            pass
        try:
            v = e['comment']
            cmd += "%scomment = %%s" % sep
            sep = ", "
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
            cmd += "%s%s = %%s" % (sep, fld)
            sep = ", "
            vlist.append(v)
        cmd += ' where id = %s'
        vlist.append(idx)
        if self.debug:
            print(cmd % tuple(vlist))
            return
        try:
            self.cur.execute(cmd, tuple(vlist))
        except _mysql_exceptions.Error as err:
            self.errorlist.append(err)

    def countInstance(self, chg):
        if len(chg) == 0:
            return 0
        cmd = "select count(*) from %s where " % self.table
        p = ""
        for v in chg:
            cmd += "%sconfig = %d" % (p, v)
            p = " or "
        try:
            self.cur.execute(cmd)
            return list(self.cur.fetchone().values())[0]
        except _mysql_exceptions.Error as err:
            self.errorlist.append(err)

    def applyConfig(self, idx):
        vals = {}
        vals.update(self.objs[idx])
        vals.update(self.cfgs[vals['config']])
        base = vals['rec_base']
        for s in self.setflds:
            #
            # Write zeros.
            # 
            for f in s:
                if self.fldmap[f]['readonly'] or vals[f] == None:
                    continue
                if self.fldmap[f]['writezero']:
                    try:
                        z = self.fldmap[f]['enum'][0]
                        haveenum = True
                    except:
                        z = 0
                        haveenum = False
                    try:
                        utils.caput(base + self.fldmap[f]['pv'], z, enum=haveenum)
                    except:
                        pass
            #
            # Write values.
            #
            for f in s:
                if vals[f] == None or self.fldmap[f]['readonly']:
                    continue
                try:
                    z = self.fldmap[f]['enum'][0]
                    haveenum = True
                except:
                    z = 0
                    haveenum = False
                try:
                    utils.caput(base + self.fldmap[f]['pv'], vals[f], enum=haveenum)
                except:
                    pass

    def diffConfig(self, idx, cfgidx=None):
        vals = {}
        vals.update(self.objs[idx])
        if cfgidx is None:
            cfgidx = vals['config']
        vals.update(self.cfgs[cfgidx])
        base = vals['rec_base']
        d = {}
        for s in self.setflds:
            for f in s:
                if vals[f] == None or self.fldmap[f]['readonly']:
                    continue
                n = base + self.fldmap[f]['pv']
                try:
                    z = self.fldmap[f]['enum'][0]
                    haveenum = True
                except:
                    haveenum = False
                v = utils.caget(n, enum=haveenum)
                if type(v) == float:
                    if v == 0.0:
                        if abs(v - vals[f]) > 0.00000001:
                            d[f] = (v, vals[f])
                    else:
                        if abs((v - vals[f])/v) > 0.00000001:
                            d[f] = (v, vals[f])
                else:
                    if v != vals[f]:
                        d[f] = (v, vals[f])
        return d

    def getActualConfig(self, idx):
        base = self.objs[idx]['rec_base']
        d = {}
        for f in self.cfgflds:
            n = base + f['pv']
            try:
                z = f['enum'][0]
                haveenum = True
            except:
                haveenum = False
            v = utils.caget(n, enum=haveenum)
            d[f['fld']] = v
        return d

    def applyAllConfigs(self):
        for i in self.objs.keys():
            self.applyConfig(i)

    def matchConfigs(self, pattern, substr=True, ci=True):
        p = pattern.replace("_","\_").replace("%","\%").replace("*", "%").replace(".", "_")
        if substr:
            p = "%"+p+"%"
        self.cur.execute("select name from %s_cfg where name %slike '%s'" %
                         (self.table, "collate latin1_general_ci " if ci else "", p))
        return [d['name'] for d in self.cur.fetchall()]
