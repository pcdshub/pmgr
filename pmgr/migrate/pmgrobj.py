import time
import datetime
import re

import MySQLdb as mdb
try:
    import _mysql_exceptions
except ImportError:
    import MySQLdb._exceptions as _mysql_exceptions
import pyca

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
#           The keys are a few boilerplate keys (id, config, owner, etc.)
#           and the configuration fields.  Note that due to inheritance
#           and mutual exclusion, many of these fields could be "None".
#     objs
#         - An object ID to object dictionary mapping.  The keys are a 
#           few boilerplate keys (id, config, owner, etc.) and the
#           object-only fields (the objflds with the 'obj' key value True).
#     groupids
#         - A list of group IDs.
#     groups
#         - A group ID to group information dictionary mapping.  The group
#           information dictionary keys are either integers (which map to
#           a dictionary giving a config and port for that group element)
#           or "global" (which maps to a dictionary with keys "name" and "len".)
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
#         - Returns a mask of DB_CONFIG, DB_OBJECT, and DB_GROUP indicating
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
#     groupDelete(idx)
#         - Delete an existing configuration group.
#     groupInsert(d)
#         - Insert a new configuration group.  d is a dictionary which maps from
#           integers (group element indices) to a dictionary with config/port indices.
#     groupUpdate(idx, d)
#         - Change an existing configuration group. d is the same as the groupInsert
#           dictionary.
#     countInstance(cfglist)
#         - Return a count of objects that depend on one of the listed configurations.
#     getAutoCfg(d)
#         - Given an object dictionary, find and return the most recently used
#           configuration that has the autoconfig field set to a matching value.
#           First look in this hutch, then in any hutch.  If none is found, return
#           an empty dictionary.
#     getConfig(idx)
#         - Expand the configuration to deal with parentage.  cfgs[idx] could have
#           many "None" values which are inherited, and this routine will fill them
#           out and set the "_haveval" key to a dictionary indicating which fields
#           have values set by the configuration itself (True) and which are inherited
#           (False).
#     applyConfig(idx)
#         - Given an object ID, apply its current configuration to it.
#     applyAllConfigs()
#         - Apply the current configuration to all objects.

class pmgrobj(object):
    DB_CONFIG = 1
    DB_OBJECT = 2
    DB_GROUP  = 4
    DB_CFGGRP = 8
    DB_ALL    = 7

    ORDER_MASK    = 0x0003ff
    SETMUTEX_MASK = 0x000200
    MUST_WRITE    = 0x000400
    WRITE_ZERO    = 0x000800
    AUTO_CONFIG   = 0x001000
    READ_ONLY     = 0x002000

    unwanted = ['seq', 'owner', 'id', 'category', 'dt_created',
                'date', 'dt_updated', 'name', 'action', 'rec_base', 'comment']

    def __init__(self, table, hutch, debug=False, prod=True):
        self.table = table
        self.hutch = hutch
        self.debug = debug
        self.cfgs = None
        self.objs = None
        self.groupids = []
        self.groups = {}
        self.errorlist = []
        self.autoconfig = None
        self.in_trans = False
        if prod:
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
        self.lastgrp = datetime.datetime(1900,1,1,0,0,1)
        self.hutchlist = self.getHutchList()
        self.checkForUpdate()
        self.updateTables()

    def readFormat(self):
        self.cur.execute("describe %s" % self.table)
        locfld = [(d['Field'], m2pType(d['Type']), d['Null'], d['Key']) for d in self.cur.fetchall()]
        locfld = locfld[10:]   # Skip the standard fields!

        self.cur.execute("describe %s_cfg" % self.table)
        fld = [(d['Field'], m2pType(d['Type']), d['Null'], d['Key']) for d in self.cur.fetchall()]
        fld = fld[7:]         # Skip the standard fields!

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
            alias[f] = createAlias(f)
            colorder[f] = 1000
            setorder[f] = 0
            mutex[f] = 0
            tooltip[f] = ''
            nullok[f] = ((nl == 'YES') or (t != str))
            unique[f] = k == "UNI"
        for (f, t, nl, k) in fld:
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
                if n[-4:] != '_grp' and n != 'config':
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
                self.cur.execute("select * from %s_update where tbl_name = 'config' or tbl_name = '%s' or tbl_name = '%s'" %
                                 (self.table, self.hutch, self.hutch + "_grp"))
            for d in self.cur.fetchall():
                if d['tbl_name'] == 'config':
                    if d['dt_updated'] > self.lastcfg:
                        self.lastcfg = d['dt_updated']
                        v = v | self.DB_CONFIG
                elif d['tbl_name'][-4:] == "_grp":
                    if d['dt_updated'] > self.lastgrp:
                        self.lastgrp = d['dt_updated']
                        v = v | self.DB_GROUP
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
        elif kind == self.DB_OBJECT:
            if self.hutch is None:
                ext = ""
            else:
                ext = " where owner = '%s' or id = 0" % self.hutch
        elif kind == self.DB_GROUP:
            if self.hutch is None:
                ext = "_grp"
            else:
                ext = "_grp where owner = '%s'" % self.hutch
        else: # self.DB_CFGGRP
            ext = "_cfg_grp"
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
        if (mask & self.DB_GROUP) != 0:
            grps = self.readDB(self.DB_GROUP)
            cfggrp = self.readDB(self.DB_CFGGRP)
            if grps == []:
                mask &= ~self.DB_GROUP
            else:
                self.groupids   = []
                self.groups     = {}
                for g in grps:
                    id = g['id']
                    self.groupids.append(id)
                    self.groups[id] = {}
                    try:
                        self.groups[id]['global'] = {'len' : 0, 'name' : g['name'], 'active': g['active']}
                    except:
                        print(g)
                        raise
                for g in cfggrp:
                    id = g['group_id']
                    if id in self.groups.keys():
                        self.groups[id][g['dispseq']] = {'config': g['config_id'],
                                                         'port': g['port_id']}
                        sz = self.groups[id]['global']['len'] + 1
                        self.groups[id]['global']['len'] = sz
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
        cmd = "insert %s_cfg (name, config, owner, mutex, dt_updated" % self.table
        vals = d['_val']
        for f in self.cfgflds:
            fld = f['fld']
            if vals[fld]:
                cmd += ", " + fld
        cmd += ") values (%s, %s, %s, %s, now()"
        vlist = [d['name']]
        vlist.append(d['config'])
        vlist.append(self.hutch)
        vlist.append(d['mutex'])
        for f in self.cfgflds:
            fld = f['fld']
            if vals[fld]:
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
        try:
            v = e['owner']
            cmd += "%sowner = %%s" % sep
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

    def groupClear(self, id):
        if self.debug:
            print("delete from %s_cfg_grp where group_id = %d" % (self.table, id))
            return True
        try:
            self.cur.execute("delete from %s_cfg_grp where group_id = %%s" % self.table, (id, ))
            return True
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            return False

    def groupDelete(self, id):
        if not self.groupClear(id):
            return False
        if self.debug:
            print("delete from %s_grp where id = %d" % (self.table, id))
            return True
        try:
            self.cur.execute("delete from %s_grp where id = %%s" % self.table, (id, ))
            return True
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            return False

    def groupInsert(self, g):
        if self.debug:
            print("insert %s_grp (name, owner, active, dt_created, dt_updated) values (%s, %s, 0, now(), now())" % \
                  (self.table, g['global']['name'], self.hutch))
            print("select last_insert_id()")
            id = self.dbgid
            self.dbgid += 1
        else:
            try:
                self.cur.execute("insert %s_grp (name, owner, active, dt_created, dt_updated) values (%%s, %%s, 0, now(), now())" \
                                 % self.table, (g['global']['name'], self.hutch))
                self.cur.execute("select last_insert_id()")
                id = list(self.cur.fetchone().values())[0]
            except _mysql_exceptions.Error as e:
                self.errorlist.append(e)
                return False
        self.groupUpdate(id, g)

    def groupUpdate(self, id, g):
        if not self.groupClear(id):
            return False
        keys = g.keys()
        keys.remove('global')
        keys.sort()
        seq = 0
        for k in keys:
            if g[k]['config'] != 0:
                try:
                    cmd = "insert %s_cfg_grp (group_id, config_id, port_id, dispseq)" % self.table
                    cmd += "values (%s, %s, %s, %s)"
                    try:
                        port = str(g[k]['port'])
                    except:
                        port = "0"
                    if self.debug:
                        print(cmd % (str(id), str(g[k]['config']), port, str(seq)))
                    else:
                        self.cur.execute(cmd, (id, g[k]['config'], port, seq))
                    seq += 1
                except _mysql_exceptions.Error as e:
                    self.errorlist.append(e)
                    return False
        try:
            cmd = "update %s_grp set active = %%s, name = %%s, dt_updated = now() where id = %%s" % self.table
            if self.debug:
                print(cmd % (g['global']['active'], id))
            else:
                self.cur.execute(cmd, (g['global']['active'], g['global']['name'], id))
            return True
        except _mysql_exceptions.Error as e:
            self.errorlist.append(e)
            return False

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

    def getAutoCfg(self, d):
        f = self.autoconfig
        v = d[f]
        cmd = "select max(seq) from %s_log where %s = %%s and owner = %%s and action != 'delete' group by id" % \
              (self.table, f)
        if self.debug:
            print(cmd % (v, self.hutch))
        try:
            if self.cur.execute(cmd, (v, self.hutch)) != 1:
                # Couldn't find it in our hutch, look in any!
                cmd = "select max(seq) from %s_log where %s = %%s and action != 'delete' group by id" % \
                      (self.table, f)
                if self.debug:
                    print(cmd % (v))
                self.cur.execute(cmd, (v))
            seq = list(self.cur.fetchone().values())[0]
            cmd = "select * from %s_log where seq = %%s" % (self.table)
            if self.debug:
                print("debug?")
                print(cmd % seq)
            self.cur.execute(cmd, seq)
            r = self.cur.fetchone()
            try:
                del r[f]
            except:
                pass
            for f in self.unwanted:
                try:
                    del r[f]
                except:
                    pass
            try:
                # See the comment in ObjModel.setValue.  This is just bizarreness.
                r['cfgname'] = r['config']
                del r['config']
            except:
                pass
            return r
        except _mysql_exceptions.Error as err:
            print(err)
            return {}

    def getConfig(self, idx, loop=[]):
        if idx == None or idx in loop:
            return {}
        d = {}
        d.update(self.cfgs[idx])
        haveval = {}
        v = d['mutex']
        if d['config'] != None:
            lp = list(loop)
            lp.append(idx)
            vals = self.getConfig(d['config'], lp)   # Get the parent configuration
            pmutex = vals['curmutex']
            mutex = ""                               # Build the mutex from the set and inherited values.
            for i in range(len(self.mutex_sets)):
                if self.mutex_obj[i]:
                    mutex += ' '
                elif v[i] != ' ':
                    mutex += v[i]
                else:
                    mutex += pmutex[i]
            d['curmutex'] = mutex
        else:
            d['curmutex'] = v
        for (k, v) in d.items():
            if k[:3] != 'PV_' and k[:4] != 'FLD_':
                continue
            if v == None:
                # This key might have a value because it is the unset element of a mutex set!
                haveval[k] = chr(self.fldmap[k]['colorder']+0x40) in d['curmutex']
            else:
                haveval[k] = True
            if not haveval[k]:
                try:
                    d[k] = vals[k]     # Try to get the parent value.
                except:
                    d[k] = None
        d['_haveval'] = haveval
        return d
