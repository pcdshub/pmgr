# This file contains all methods that use the pmgrobj interface included by
# Mike in the parameter manager.
import psp.Pv as pv

# Wrapper to time these utils. If they take too long, they are not useful.
import time
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print "{0} function took {1:0.3f} s".format(f.func_name, time2-time1)
        return ret
    return wrap

### Higher-level functions, called directly in main.py
def config(pmgr, PV):
    d = pmgrConfig(pmgr, PV)
    return d["name"]

def pvConfig(pmgr, PV):
    """ Returns live config dict associated with PV, or None """
    configFields = listCfgFields(pmgr)
    cfgDict = {}
    for field in configFields:
        if field != "FLD_TYPE":
            pvExt = pmgr.fldmap[field]["pv"]
            val = pv.get(PV + pvExt)
            if val is None:
                return None
            fieldDict = pmgr.fldmap[field]
            if "enum" in fieldDict:
                choices = fieldDict["enum"]
                if val >= len(choices):
                    print "WARNING: index mismatch in field {0}.".format(field) 
                    print "An ioc has been updated without updating the Parameter Manager!"
                    val = len(choices) - 1
                val = fieldDict["enum"][val]
            cfgDict[field] = val
    return cfgDict

def pmgrConfig(pmgr, PV):
    """ Returns config dict associated with PV in the pmgr, or None """
    obj = objFromPV(pmgr, PV)
    pmgr.updateTables()
    cfg = pmgr.objs[obj]["config"]
    d = cfgVals(pmgr, cfg)
    return d

def nameConfig(pmgr, name):
    """ Returns config dict associated with configuration name """
    ID = cfgFromName(pmgr, name)
    cfg = cfgVals(pmgr, ID)
    return cfg

def newConfig(pmgr, cfgDict, name, typeStr=None, parent=None, owner=None):
    """
    Creates and saves a new config from cfgDict and the passed in parameters.
    Input parent can be a string or the integer ID. By default, parent and
    owner are those associated with this pmgr. (e.g. XPP and xpp). Returns
    None in event of a failure.
    """
    if not cfgDict or not name:
        return None
    configFields = listCfgFields(pmgr)
    for field in configFields:
        if field not in cfgDict:
            cfgDict[field] = None # configInsert freaks out over missing fields
    if not parent:
        parent = getHutch(pmgr).upper()
    if type(parent) == str:
        parent = cfgFromName(pmgr, parent)
    if not owner:
        owner = getHutch(pmgr)
    if not typeStr:
        typeStr = "{0}_{1}".format(name, owner)
        typeStr = nextType(pmgr, typeStr)
    cfgDict["config"] = parent
    cfgDict["owner"] = owner
    cfgDict["FLD_TYPE"] = typeStr
    cfgDict["name"] = name
    ID = cfgInsert(pmgr, cfgDict)
    return ID

def setConfig(pmgr, PV, config):
    """ Sets the config name config to the object associated with PV """
    obj = objFromPV(pmgr, PV)
    if not obj:
        print "Error connecting to PV {0}".format(PV)
        return False
    cfg = cfgFromName(pmgr, config)
    if not cfg:
        print "No configuration found for name {0}".format(config)
        return False
    return setObjCfg(pmgr, obj, cfg)

def applyConfig(pmgr, PV):
    """ Applies the config assigned to PV to the live values """
    obj = objFromPV(pmgr, PV)
    objApply(pmgr, obj)
    # Unfortunately, the apply configurations interface has no error returns.
    # We will not return True/False like the others and instead check in post
    # with a diff in main.

def defaultName(pmgr, PV):
    """ Returns a default name for the config associated with PV """
    name = pv.get(PV + ".DESC")
    return nextName(pmgr, name)

def nextName(pmgr, name):
    """
    Returns name if it's available and valid. Otherwise, appends numbers until
    a valid name is found, returning the new name.
    """
    allNames = allCfgNames(pmgr) 
    name = incrementMatching(name, allNames, maxLength=15)
    return name

def hutchCfgNames(pmgr, hutch):
    return setOfAllCfgVal(pmgr, "name", "owner", hutch)

def allCfgNames(pmgr):
    return setOfAllCfgVal(pmgr, "name")

def getAuto(pmgr, PV, reInit):
    go = checkCanAuto(pmgr, PV)
    if not go:
        return "Object is not auto-configurable."
    if reInit:
        fixSN(pmgr, PV)
    d = autoCfg(pmgr, PV)
    if not d:
        return "No autoconfig found."
    return d

def setDesc(pmgr, PV, desc):
    objID = objFromPV(pmgr, PV)
    obj = pmgr.objs[objID]
    obj["FLD_DESC"] = desc
    return transaction(pmgr, "objectChange", objID, obj)

def changeConfig(pmgr, cfgName, **kwargs):
    idx = cfgFromName(pmgr, cfgName)
    cfgd = {}
    nChange = 0
    for field, value in kwargs.items():
        ftry = findValidCfgField(pmgr, field)
        if ftry is None:
            print "{0} is not a valid field.".format(field)
        else:
            cfgd[ftry] = value
            nChange += 1
    didWork = cfgChange(pmgr, idx, cfgd)
    if didWork:
        return nChange
    else:
        return 0

### Mid-level functions, called by higher-level functions
def nextType(pmgr, typeStr):
    allTypes = setOfAllCfgVal(pmgr, "FLD_TYPE")
    typeStr = incrementMatching(typeStr, allTypes)
    return typeStr

def cfgInsert(pmgr, cfg):
    """ Adds partial configuration dict cfg to pmgr as a configuration. """
    if "mutex" not in cfg:
        cfg["mutex"] = "XY  "
    cfg["_haveval"] = {} # We need this to appease configInsert
    for field in cfg.keys():
        if cfg[field] is None:
            cfg["_haveval"][field] = False
        else:
            cfg["_haveval"][field] = True
    cfg["_val"] = cfg["_haveval"] # Workaround for typo in pmgrobj.py
    result = None
    result = transaction(pmgr, "configInsert", cfg)
    return result

def setObjCfg(pmgr, objID, cfgID):
    pmgr.updateTables()
    d = pmgr.objs[objID]
    d["config"] = cfgID
    result = transaction(pmgr, "objectChange", objID, d)
    if result and result == "error":
        return False
    return True

def objApply(pmgr, objID):
    result = transaction(pmgr, "applyConfig", objID)
    if result and result == "error":
        return False
    return True

def getHutch(pmgr):
    return pmgr.hutch

def listCfgFields(pmgr):
    return listFieldsWith(pmgr, "obj", False)

def setOfAllCfgVal(pmgr, field, fcheck=None, fval=None):
    """
    Returns a set of all configured values for field.
    kwargs is a dict of field : value pairs that act as conditions for being
    on this list. With no kwargs we return all of the values.
    """
    vals = set()
    pmgr.updateTables()
    for cfg in pmgr.cfgs:
        d = pmgr.cfgs[cfg]
        if fcheck and fval:
            if d[fcheck] == fval:
                vals.add(d[field])
        else:
            vals.add(d[field])
    return vals

def objFromPV(pmgr, PV):
    """ Returns objID associated with PV, or None """
    return firstObjWith(pmgr, "rec_base", PV)

def cfgFromName(pmgr, name):
    """ Returns cfgID associated with name, or None """
    return firstCfgWith(pmgr, "name", name)

def incrementMatching(text, matchSet, maxLength=None, n=2):
    """
    Adds incrementing n-digit numbers to text until it no longer matches any
    entries on matchSet.
    """
    if maxLength is not None and len(text) > maxLength:
        text = text[0:maxLength]
    while text in matchSet:
        if text[-n:].isdigit():
            num = int(text[-n:])
            num += 1
            num = str(num)
            while len(num) < n:
                num = "0" + num
            text = text[:-n]
        else:
            num = "0" * n
        if maxLength is not None and len(text) > maxLength-n:
            text = text[0:maxLength-n]
        text += num
    return text

def fixSN(pmgr, PV):
    pv.put(PV + ".RINI", 1) # Re-initialize motor to get accurate SN
    objID = objFromPV(pmgr, PV)
    pmgr.updateTables()
    d = pmgr.objs[objID]
    # Set up Pv object so we can specify a timeout and wait for init.
    SNPV = pv.Pv(PV + ".SN")
    SNPV.connect(timeout=5)
    SN = SNPV.get() # Pull the value we need
    SNPV.disconnect()
    d["FLD_SN"] = SN
    transaction(pmgr, "objectChange", objID, d)
    
def autoCfg(pmgr, PV):
    objID = objFromPV(pmgr, PV)
    pmgr.updateTables()
    objDict = pmgr.objs[objID]
    auto = transaction(pmgr, "getAutoCfg", objDict)
    if auto:
        cfgID = auto["cfgname"]
    else:
        return {}
    return cfgVals(pmgr, cfgID)

def checkCanAuto(pmgr, PV):
    objID = objFromPV(pmgr, PV)
    pmgr.updateTables()
    obj = pmgr.objs[objID]
    mode = obj["category"]
    return mode == "Auto"

def findValidCfgField(pmgr, field):
    flds = listCfgFields(pmgr)
    choices = [field, field.lower(), field.upper(), "FLD_" + field.upper()]
    for c in choices:
        if c in flds:
            return c
    return None

def cfgChange(pmgr, idx, cfgd):
    return transaction_bool(pmgr, "configChange", idx, cfgd)

def transaction_bool(pmgr, method, *args):
    """
    Does transaction, but returns True if successful and False if errors
    instead of normal output if successful and "error" if errors.
    """
    output = transaction(pmgr, method, *args)
    if output == "error":
        return False
    return True


### Lower-level functions, called by mid-level functions
def cfgVals(pmgr, idx):
    pmgr.updateTables()
    d = pmgr.getConfig(idx)
    del d["dt_updated"]
    del d["_haveval"]
    return d

def listFieldsWith(pmgr, property, value):
    """ Returns a list of field names where property = value """
    fWith = []
    pmgr.updateTables()
    for field in pmgr.objflds:
        if field[property] == value:
            fWith += [field["fld"]]
    return fWith

def firstObjWith(pmgr, field, val):
    """ Returns the first objID found where field is value """
    pmgr.updateTables()
    for obj in pmgr.objs.keys():
        if pmgr.objs[obj][field] == val:
            return obj
    return None

def firstCfgWith(pmgr, field, val):
    """ Returns the first cfgID found where field is value """
    pmgr.updateTables()
    for cfg in pmgr.cfgs.keys():
        if pmgr.cfgs[cfg][field] == val:
            return cfg
    return None

def transaction(pmgr, method, *args):
    """
    Does a safe database transaction using pmgrobj.pmgrmethod(*args). Prints
    error strings to the terminal. Always closes transactions.
    """
    pmgr.updateTables()
    pmgr.start_transaction()
    try:
        output = getattr(pmgr, method)(*args)
    finally:
        errors = pmgr.end_transaction()
        if errors:
            for e in errors:
                print e
            output = "error"
        pmgr.updateTables()
        return output

