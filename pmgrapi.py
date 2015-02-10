import MySQLdb as mdb
import re

#
# A general API for the parameter manager.  This is a lot of code copied from db.py.
#
# class pmgrapi(type, hutch)
#      Create a parameter manager instance to manage the particular type of objects for a
#      particular hutch.  This also initializes the field information for this type of
#      object.
#
# Members:
#      objs:       An object ID -> information dictionary.
#      cfgs:       A configuration ID -> information dictionary.
#      objnames:   An object name -> object ID dictionary.
#      cfgnames:   An configuration name -> configuration ID dictionary.
#      mutex_sets: A list of dependency sets.  (One item in each set is derived from the others.)
#      objflds:    A list of all field information dictionaries, sorted by set order.
#      cfgflds:    A list of field information directories that make up a configuration
#                  (a subset of objflds).
#      fldmap:     A field name -> information dictionary.
#      colmap:     A colorder (ID) -> information directory.
#      setflds:    A list of lists of fieldnames, sorted by set order.
#
# Information dictionaries:
#      field dictionary:
#          fld        Name of the field.
#          pv         The "PV" style name of the field (to be appended to the basename).
#          alias      A human-readable alias.
#          type       A python type for this field: str, int, or float.
#          colorder   The column order for the GUI (also used as a unique ID).
#          setorder   The order in which the field should be written (0 first, then 1, etc.)
#          mustwrite  Does this field need to be written even if the value is the same?
#          writezero  Does this field need to be cleared before writing a value?
#          setmutex   Is this field part of a dependency set?
#          tooltip    A tooltip that describes this field.
#          mutex      A list of the dependency sets for this field. (Indices into mutex_sets.)
#          enum       If an enumerated type, a list of allowed values. (type will be str!)
#          obj        True if this field is attached to an object, False if it is part of a configuration.
#          objidx     The index of this field in objflds.
#          cfgidx     The index of this field in cfgflds, if obj is False.
#
#      object dictionary:
#          owner      The hutch that owns this object.
#          dt_created Timestamp of object creation.
#          dt_updated Timestamp of object modification.
#          id         A unique integer ID for this object.
#          name       A unique name for this object.
#          config     The configuration ID for this object.
#          cfgname    The configuration name for this object.
#          rec_base   The PV base name for this object.
#          mutex      A list of which fields in this object are derived values.  (There is one
#                     entry in this list for each item in mutex_sets.  Some of these may be None,
#                     if the fields are from the configuration, not the object.)
#      In addition, all fields in objflds with obj == True have values in this dictionary.
#
#      configuration directory
#          owner      The hutch that owns this configuration, or None if this is global.
#          id         A unique integer ID for this configuration.
#          name       A unique name for this configuration.
#          config     The parent configuration ID.
#          cfgname    The parent configuration name.
#          dt_updated Timestamp of configuration modification.
#          security   An unused string to be used for security purposes.
#          mutex      A list of which fields in this object are derived values.  (There is one
#                     entry in this list for each item in mutex_sets.  Some of these may be None,
#                     if the fields are from the object, or if the derived value is inherited
#                     from the parent configuration.)
#      In addition, all fields in objflds with obj == False have values in this dictionary.
#
# Methods:
# bool readDB()
#      Retrieve a snapshot of the database.  Returns true if successful.
# getAllObjects()
#      Return a list of object names.
# getAllConfigurations()
#      Return a list of configuration names.
# getConfiguration(name)
#      Returns a tuple of two dictionaries: the first is the values in this configuration, the second is the
#      *inherited* values.
# getObject(name)
#      Returns a dictionary containing the object configuration.

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

class pmgrapi(object):
    objstd = ['id', 'config', 'owner', 'name', 'rec_base', 'mutex', 'dt_created', 'dt_updated']
    cfgstd = ['id', 'name', 'config', 'security', 'owner', 'dt_updated', 'mutex']

    ORDER_MASK    = 0x0003ff
    SETMUTEX_MASK = 0x000200
    MUST_WRITE    = 0x000400
    WRITE_ZERO    = 0x000800
    
    def __init__(self, type, hutch):
        self.table = type
        self.hutch = hutch
        try:
            self.con = mdb.connect('psdb', 'pscontrols', 'pcds', 'pscontrols');
            self.cur = self.con.cursor(mdb.cursors.DictCursor)
            self.cur.execute("call init_pcds()")
        except:
            return

        self.cur.execute("describe %s" % self.table)
        locfld = [(d['Field'], m2pType(d['Type'])) for d in self.cur.fetchall()]
        locfld = locfld[len(self.objstd):]   # Skip the standard fields!

        self.cur.execute("describe %s_cfg" % self.table)
        fld = [(d['Field'], m2pType(d['Type'])) for d in self.cur.fetchall()]
        fld = fld[len(self.cfgstd):]         # Skip the standard fields!
        self.cfgfldcnt = len(fld)
        self.objfldcnt = len(locfld) + self.cfgfldcnt

        self.cur.execute("select * from %s_name_map" % self.table)
        result = self.cur.fetchall()

        alias = {}
        colorder = {}
        setorder = {}
        tooltip = {}
        enum = {}
        mutex = {}
        mutex_sets = []
        for i in range(16):
            mutex_sets.append([])
        for (f, t) in locfld:
            alias[f] = createAlias(f)
            colorder[f] = 1000
            setorder[f] = 0
            mutex[f] = 0
            tooltip[f] = ''
        for (f, t) in fld:
            alias[f] = createAlias(f)
            colorder[f] = 1000
            setorder[f] = 0
            mutex[f] = 0
            tooltip[f] = ''

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
        # We're assuming the bits are used from LSB to MSB, no gaps!
        self.mutex_sets = [l for l in mutex_sets if l != []]
        self.mutex_cnt = len(self.mutex_sets)
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
        for (f, t) in locfld:
            n = fixName(f)
            so = setorder[f] & self.ORDER_MASK
            setset.add(so)
            d = {'fld': f, 'pv': n, 'alias' : alias[f], 'type': t,
                 'colorder': colorder[f], 'setorder': so,
                 'mustwrite': (setorder[f] & self.MUST_WRITE) == self.MUST_WRITE,
                 'writezero': (setorder[f] & self.WRITE_ZERO) == self.WRITE_ZERO,
                 'setmutex': (setorder[f] & self.SETMUTEX_MASK) == self.SETMUTEX_MASK,
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
        for (f, t) in fld:
            n = fixName(f)
            so = setorder[f] & self.ORDER_MASK
            setset.add(so)
            d = {'fld': f, 'pv': n, 'alias' : alias[f], 'type': t,
                 'colorder': colorder[f], 'setorder': so,
                 'mustwrite': (setorder[f] & self.MUST_WRITE) == self.MUST_WRITE,
                 'writezero': (setorder[f] & self.WRITE_ZERO) == self.WRITE_ZERO,
                 'setmutex': (setorder[f] & self.SETMUTEX_MASK) == self.SETMUTEX_MASK,
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
        self.colmap = {}
        for i in range(len(self.objflds)):
            d = self.objflds[i]
            d['objidx'] = i
            self.fldmap[d['fld']] = d
            self.colmap[d['colorder']] = d
        self.cfgflds = [d for d in self.objflds if d['obj'] == False]
        for i in range(len(self.cfgflds)):
            self.cfgflds[i]['cfgidx'] = i
        setset = list(setset)
        setset.sort()
        self.setflds = [setflds[i] for i in setset]
        self.objs = {}
        self.cfgs = {}
        self.con.commit()

    def readDB(self):
        try:
            self.cur.execute("select * from %s_cfg" % (self.table))
            cfgs =  list(self.cur.fetchall())
            self.cur.execute("select * from %s where owner = '%s' or id = 0" % (self.table, self.hutch))
            objs =  list(self.cur.fetchall())
        except:
            return False
        map = {}
        namemap = {}
        for d in cfgs:
            map[d['id']] = d
            namemap[d['name']] = d['id']
        self.cfgs = map
        self.cfgnames = namemap
        for d in cfgs:
            r = d['config']
            if r == None:
                d['cfgname'] = ""
            else:
                d['cfgname'] = self.cfgs[r]['name']
            m = []
            ms = d['mutex']
            for i in range(len(self.mutex_sets)):
                if ms[i] == ' ':
                    m.append(None)
                else:
                    m.append(self.colmap[ord(ms[i])-0x40]['fld'])
            d['mutex'] = m
        map = {}
        namemap = {}
        for o in objs:
            map[o['id']] = o
            namemap[o['name']] = d['id']
            o['cfgname'] = self.cfgs[o['config']]['name']
            m = []
            ms = o['mutex']
            for i in range(len(self.mutex_sets)):
                if ms[i] == ' ':
                    m.append(None)
                else:
                    m.append(self.colmap[ord(ms[i])-0x40]['fld'])
            o['mutex'] = m
        self.objs = map
        self.objnames = namemap
        self.con.commit()
        return True

    def getAllObjects(self):
        return self.objnames.keys()

    def getAllConfigurations(self):
        return self.cfgnames.keys()

    def getConfiguration(self, name):
        try:
            d = dict(self.cfgs[self.cfgnames[name]])
        except:
            return (None, None)
        if d['cfgname'] == "":
            return (d, {})
        (pc, pi) = self.getConfiguration(d['cfgname'])
        pi.update(pc)
        for f in d.keys():
            if d[f] == None and f != 'owner' and not f in d['mutex']:
                del d[f]
            else:
                del pi[f]
        return (d, pi)

    def getObject(self, name):
        try:
            return dict(self.objs[self.objnames[name]])
        except:
            return None
            
    def createObject(self, name, d):
        pass

    def createConfiguration(self, name, d):
        pass

    def updateObject(self, name, d):
        pass

    def updateConfiguration(self, name, d):
        pass

    def applyConfiguration(self, olist=None):
        if olist == None:
            olist = self.getAllObjects()
        pass
