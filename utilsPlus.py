# An Extension of utils to provide lower and mid level functions surrounding 
# pmgrUtils. It is a mishmash of functions compiled into one script so it is
# to refer to it only when trying to understand specific funtions in pmgrUtils.

import psp.Pv as pv
import logging
import subprocess
import os
import string
import datetime
                 
from pprint import pprint
from pmgrobj import pmgrobj
from os import system
from ConfigParser import SafeConfigParser

logger = logging.getLogger(__name__)

# Globals
maxLenName = 42
parser = SafeConfigParser()
parser.read(os.path.dirname(os.path.abspath(__file__)) + "/pmgrUtils.cfg")

# To add hutches or objTypes to the supported list, look in pmgrUtils.cfg
supportedHutches = parser.get("pmgr", "supportedHutches")
supportedObjTypes = parser.get("pmgr", "supportedObjTypes")

nTries = 3                                # Number of attempts when using caget

def getCfgVals(pmgr, PV):
    """ Returns a dictionary of the live cfg fields associated with a PV """
    PV = PV.upper()
    configFields = listCfgFields(pmgr)
    cfgDict = getFieldDict(pmgr, PV, configFields)

    name = None

    try:
        name = pv.get(PV +".DESC")
    except:
        name = "Unknown"
    
    cfgDict["name"] = name
    cfgDict["FLD_TYPE"] = "{0}_{1}".format(name, PV[:4])

    return cfgDict

def getObjVals(pmgr, PV):
    """ Returns a dictionary of the live obj fields associated with a PV """
    PV = PV.upper()
    objectFields = listObjFields(pmgr)
    objDict = getFieldDict(pmgr, PV, objectFields)
    objDict["rec_base"] = PV
    
    name = None

    if objDict["FLD_DESC"]:
        name = objDict["FLD_DESC"]
    elif objDict["FLD_SN"]:
        name = "SN:{0}".format(objDict["FLD_SN"])
    else:
        name = "Unknown"

    # Make sure the SN is a 9 digit string *with* the leading zero if necessary
    objDict = checkSNLength(objDict, pmgr)

    objDict["name"] = name
    
    return objDict

def newObject(pmgr, objDict,typeStr=None, parent=None, owner=None):

    if "MFI" in objDict["FLD_PN"]:
        category = "Manual"
    elif "MDI" in objDict["FLD_PN"]:
        category = "Auto"
    else:
        category = "Protected"

    objectFields = listObjFields(pmgr)

    # Pmgr doesnt handle missing fields well
    for field in objectFields:
        if field not in objDict:
            objDict[field] = "None" 

    if not parent:
        parent = getHutch(pmgr).upper()
    if type(parent) == str:
        parent = cfgFromName(pmgr, parent)
    if not owner:
        owner = getHutch(pmgr)
    if "comment" not in objDict:
        objDict["comment"] = "None"
    if "rec_base" not in objDict:
        objDict["rec_base"] = "Unknown"

    objDict["config"] = parent
    objDict["owner"] = owner
    objDict["FLD_TYPE"] = typeStr
    objDict["category"] = category
    
    objID = objInsert(pmgr, objDict)

    return objID

def objInsert(pmgr, objDict):
    """ Adds partial configuration dict obj to pmgr as a configuration. """
    if "mutex" not in objDict:
        objDict["mutex"] = "XY  "
    if "rec_base" not in objDict:
        objDict["mutex"] = "Unknown PV"
    objDict["_haveval"] = {} # We need this to appease configInsert
    for field in objDict.keys():
        if objDict[field] is None:
            objDict["_haveval"][field] = False
        else:
            objDict["_haveval"][field] = True
    objDict["_val"] = objDict["_haveval"] # Workaround for typo in pmgrobj.py
    result = None

    pmgr.updateTables()
    pmgr.start_transaction()
    
    output = pmgr.objectInsert(objDict)
    errors = pmgr.end_transaction()

    return output

def nextObjName(pmgr, name):
    """
    Returns name if it's available and valid. Otherwise, appends numbers until
    a valid name is found, returning the new name.
    """
    allNames = allObjNames(pmgr)
    name = incrementMatching(str(name), allNames, maxLength=maxLenName)
    return str(name)

def nextCfgName(pmgr, name):

    """ 
    Wrapper function for nextName that just makes sure the name is of type str
    """
    allNames = allCfgNames(pmgr)
    name = incrementMatching(str(name), allNames,  maxLength=maxLenName)
    return str(name)

def objUpdate(pmgr, idx, objDict):
    """ Updates the obj using the fields specified in objDict """
    obj = pmgr.objs[idx]
    for field in objDict.keys():
        try: obj[field] = objDict[field]
        except: continue
    return transaction(pmgr, "objectChange", idx, obj)

def cfgUpdate(pmgr, idx, cfgDict):
    """ Updates the cfg using the fields specified in cfgDict """
    cfg = pmgr.cfgs[idx]
    for field in cfgDict.keys():
        try: cfg[field] = cfgDict[field]
        except: continue
    return transaction(pmgr, "configChange", idx, cfg)


def get_motor_PVs(partialPV):
    motorPVs = []
    i = 1
    while i != 40:
        basePV = "%s:%02d"%(partialPV, i)
        print basePV
        try:
            SN = pv.get(basePV + ".SN")
            if len(SN) >= 8:
                motor_PVs[sn] = basepv
                print "PV: {0} is active".format(basePV)
                motorPVs += basePV
        except: pass
    return motorPVs

def allObjNames(pmgr):
    return setOfAllObjVal(pmgr, "name")

def setOfAllObjVal(pmgr, field, fcheck=None, fval=None):
    """
    Returns a set of all configured values for field.
    kwargs is a dict of field : value pairs that act as conditions for being
    on this list. With no kwargs we return all of the values.
    """
    vals = set()
    pmgr.updateTables()
    for obj in pmgr.objs:
        d = pmgr.objs[obj]
        if fcheck and fval:
            if d[fcheck] == fval:
                vals.add(d[field])
        else:
            vals.add(d[field])
    return vals

def getObjWithSN(pmgr, SN, verbose):
    """
    Returns the objID of the first object with the matching SN. None if no 
    object exits. It will also pad SNs if they are less than 9 digits long
    """

    SN = str(SN)
    pmgr.updateTables()

    for objID in pmgr.objs.keys():
        pmgrSN = pmgr.objs[objID]["FLD_SN"]
        changed = False
        
        while len(pmgrSN) < 9:
            pmgrSN = "0" + pmgrSN
            changed = True
            
        if changed and pmgr.objs[objID]["name"] != "DEFAULT":
            if verbose:
                print "\nThe SN for motor {0} has an incorrect length. Adding \
zeros to ensure proper pmgr functionality.".format(pmgr.objs[objID]["name"])
            obj = pmgr.objs[objID]
            obj["FLD_SN"] = pmgrSN
            transaction(pmgr, "objectChange", objID, obj)

        if pmgrSN == SN: 
            return objID
    
    return None    

def getFieldDict(pmgr, PV, fields):
    fldDict = {}
    for field in fields:
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
            fldDict[field] = val
    return fldDict

def objChange(pmgr, idx, objd):
    return transaction_bool(pmgr, "objectChange", idx, objd)

def convertToApplyCfg(cfgDict):
    DIR = {"pos":0, "neg":0}
    EE = {"disable":0, "enable":1}
    EGAG = {"no":0, "yes":1}
    ERSV = {"no_alarm":0, "minor":1, "major":2, "invalid":3}
    FOFF = {"variable":0, "frozen":1}
    HEGE = {"pos":0, "neg":1}
    HTYP = {"n/a":0, "e mark":1, "h switch":2, "limits":3, "stall":4}
    LM = {"invalid":0, "decel, canhome":1, "decel, nohome":2, 
          "decel, stopprog":3, "nodecel, canhome":4, "nodecel, nohome":5,
          "nodecel, stopprog": 6}
    MODE = {"normal":0, "scan":1}
    SM = {"stop on stall":0, "no stop":1}
    STSV = {"no_alarm":0, "minor":1, "major":2, "invalid":3}
    S1 = {"not used":0, "home l":1, "home h":2, "limit+ l":3, "limit+ h":4,
          "limit- l":5, "limit- h":6, "5v out":7, "invalid":8}
    S2 = {"not used":0, "home l":1, "home h":2, "limit+ l":3, "limit+ h":4,
          "limit- l":5, "limit- h":6, "5v out":7, "invalid":8}
    S3 = {"not used":0, "home l":1, "home h":2, "limit+ l":3, "limit+ h":4,
          "limit- l":5, "limit- h":6, "5v out":7, "invalid":8}
    S4 = {"not used":0, "home l":1, "home h":2, "limit+ l":3, "limit+ h":4,
          "limit- l":5, "limit- h":6, "5v out":7, "invalid":8}

    enum = {"DIR":DIR, "EE":EE, "EGAG":EGAG, "ERSV":ERSV, "FOFF":FOFF, 
            "HEGE":HEGE, "HTYP":HTYP, "LM":LM, "MODE":MODE, "SM":SM, "STSV":STSV,
            "S1":S1, "S2":S2, "S3":S3, "S4":S4}

    newDict = cfgDict

    for field in enum.keys():
        newDict["FLD_"+field] = enum[field][cfgDict["FLD_"+field].lower()]

    return newDict
          

def checkSNLength(cfgDict, pmgr):
    """ 
    Function that checks to make sure the SN in the configuration dictionary is
    9 digits long. Issues have come up becasue leading zeros get dropped 
    somewhere along the pipeline. It will return a corrected configuration 
    dictionary if the SN length is wrong, and return the same one if it is fine.
    """

    # Make sure it is a string
    cfgDict["FLD_SN"] = str(cfgDict["FLD_SN"])
    
    SN = cfgDict["FLD_SN"]
    try:
        # Continue adding 0s until the SN is the correct length
        while len(cfgDict["FLD_SN"]) < 9:
            cfgDict["FLD_SN"] = "0" + cfgDict["FLD_SN"]
        return cfgDict

    # If it fails in any way just return the dictionary
    except:
        print "Failed to check SN"
        return cfgDict

def listObjFields(pmgr):
    return listFieldsWith(pmgr, "obj", True)

def listCfgFields(pmgr):
    return listFieldsWith(pmgr, "obj", False)


def createmotordb(hutch, path):
    """
    Go through all config files in $DEVICE_CONFIG_DIR and map motor
    serial number of latest config file.

    Returns a dictionary where
    - key: motor serial number
    - value: latest config file
    """
    logger.info("Creating motor configuration DB")    
    
    logger.debug("Grepping motor serial number from motor config files")
    if path:
        command_string = "grep -H '\.SN' {0}/*.cfg | sort -n -k 2".format(path)
    else:
        command_string = "grep -H '\.SN' /reg/neh/operator/{0}opr/device_config/ims/*.cfg  | sort -n -k 2".format(hutch.lower())
    
    logging.debug(command_string)
    
    grep_out = subprocess.check_output(command_string,shell=True)
    sn_list = grep_out.strip().split("\n")
        

    # loop through sn_list and build up dictionary of SN to latest
    # config
    logger.debug("Matching serial numbers of latest configuration")
    motor_db = {}  # Empty motor-db dictionary

    for sn in sn_list:
        
        # split line apart
        sn_piece = sn.split()

        # If size < 2 -- no SN recorded and should be skipped
        if len(sn_piece) < 2: continue

        # Get config file and serial number
        cfg = sn_piece[0][:-4]  # last 4 characters from grep output
                                # are always ':.SN 
        sn = sn_piece[1]

        # Add unique entries to motor-db dictionary
        if sn in motor_db.keys() :
            # Only add latest config
            logger.debug("Found another config file for SN:%s"%sn)

            db_time = os.stat(motor_db[sn]).st_mtime
            new_time = os.stat(cfg).st_mtime
            
            logger.debug("%s ==> %s"%(motor_db[sn],
                                      datetime.datetime.fromtimestamp(db_time) )
                         )
            logger.debug("%s ==> %s"%(cfg,
                                      datetime.datetime.fromtimestamp(new_time))
                         )

            if new_time > db_time :
                logger.debug("Picking new config %s"%cfg)
                motor_db[sn] = cfg
            else:
                logger.debug("Sticking with current config %s"%motor_db[sn])
        else :
            # New entry
            logger.debug("New entry=>  SN:%s CFG:%s"%(sn,cfg))
            motor_db[sn] = cfg

    logger.info("Number of saved motor configs:%d"%len(sn_list))
    logger.info("Number of unique motor configs:%d"%len(motor_db))
    return motor_db


def getImportFieldDict(cfgPath):
    '''
    Takes in a path to a cfg file, loads the text file and then parses the
    contents into a config dictionary
    '''

    cfg = open(cfgPath, 'r')
    cfgStr = cfg.readlines()

    # Remove lines sleep command lines, commented out lines and blank lines
    # from list
    cfgStr = [field[1:-1] for field in cfgStr if field != '\n' and field[0] != '#' and field[0:5] != 'sleep']

    # Remove fields that dont have a value - they will be set to None later.
    # Also add FLD
    cfgStr = ['FLD_' + field for field in cfgStr if ' ' in field ]

    # Turn the list into a dictionary using the first space as the seperator
    cfgDict = dict(map(str, field.split(' ',1)) for field in cfgStr)

    # Change appropriate values to int if changType is set to true
    for field in cfgDict:
        try: cfgDict[field] = int(cfgDict[field])
        except: 
            try: cfgDict[field] = float(cfgDict[field])
            except: pass

    if "FLD_DESC" not in cfgDict.keys():
        cfgDict["FLD_DESC"] = None
            
    if "MFI" in cfgDict["FLD_PN"]:
        cfgDict["category"] = "Manual"
    elif "MDI" in cfgDict["FLD_PN"]:
        cfgDict["category"] = "Auto"
    else:
        cfgDict["category"] = "Protected"

    return cfgDict


def updateConfig(PV, pmgr, objID, cfgID, objDict, cfgDict, allNames, verbose):
    """ Routine to update the configuration of an obj """
    # # PMGR cfg values for comparisons
    objOld = pmgr.objs[objID]
    cfgOld = pmgr.cfgs[cfgID]

    # # Print live values for troubleshooting
    if verbose:
        print "\nLive cfg values for {0}".format(pv.get(PV+".DESC"))
        pprint(objDict)
        pprint(cfgDict)

        print "\nPMGR cfg valu es for {0} before update".format(pv.get(PV+".DESC"))
        pprint(objOld)
        pprint(cfgOld)
        print


    print cfgDict["name"], objDict["name"]


    cfgDict["FLD_TYPE"] = pmgr.cfgs[cfgID]["FLD_TYPE"]
    cfgDict["name"] = objDict["name"]

    if cfgOld["name"] in allNames: allNames.remove(cfgOld["name"])
    cfgDict["name"] = incrementMatching(cfgDict["name"],
                                             allNames,
                                             maxLength=maxLenName)
    print "Saving configuration..." 
    # # Actually do the update
    didWork = cfgChange(pmgr, cfgID, cfgDict)

    return didWork, objOld, cfgOld


def motorPrelimChecks(PV, hutches, objType, verbose=False):
    """
    Runs prelimenary checks on the paramter manager inputs, and returns a 
    valid hutch name, and serial number. Returns false
    for any of the variables if there are any issues when obtaining them.
    """
    SN = False
    
    # Check for valid hutch entry
    if not hutches: hutches.append(PV[0][:3].lower())
    for hutch in hutches:
        if hutch not in supportedHutches:
            print "Invalid hutch: {0}. Only supports sxr and amo.".format(hutch.upper())
            print "Removing hutch: {0}".format(hutch.upper())
            hutches.remove(hutch)
    # Replace sxd with amo and sxr if present
    if 'sxd' in hutches:
        if 'amo' not in hutches: hutches.append('amo')
        if 'sxr' not in hutches: hutches.append('sxr')
        hutches.remove('sxd')
    if not hutches: return hutches, objType, SN
    if verbose: 
        print "Hutches: {0}".format(hutches)

    # Check for valid obj entry. Pmgr only supports ims motors as of 1/1/2016
    if str(objType) in supportedObjTypes: pass
    elif ":MMS:" in PV[0]: objType = "ims_motor"
    else:
        print "Unknown device type for {0}".format(PV[0])
        objType = False
        return hutches, objType, SN

    # Get the motor serial number via caget
    i = 0
    SN = {}

    for motorPV in PV:
        while i < nTries:
            try:
                SN[motorPV] = pv.get(motorPV + ".SN")
                break
            except: i+=1

        if not SN:
            print "Failed to get motor serial number for motor {0}".format(motorPV)
            continue

    return hutches, objType, SN
    # Wherever the function is called needs to have a check that ensures none of
    # the return values are None


def dumbMotorCheck(PV):
    """
    Takes in a PV attempts caget on the PN nTries times and then checks the PN 
    to see if it is MFI. Returns True if MFI is in the PN string, false if not.
    """
    PN = ""
    i = 0
    
    while i < nTries:
        try: 
            PN = pv.get(PV + ".PN")
            break
        except: i += 1
    
    if "MFI" in PN: return True
    else: return False


def listObjFields(pmgr):
    """ Returns the list of fields for motor objects """

    fields = []
    for field in pmgr.objflds: fields.append(field['fld'])

    return fields    


def get_all_SN(pmgr):
    """ Returns a list of all the motor SNs currently in the pmgr"""
    pmgr.updateTables()
    SNs = []
    for obj in pmgr.objs.keys():
        if pmgr.objs[obj]['FLD_SN'] > 0:
            SNs.append(pmgr.objs[obj]['FLD_SN'])
    
    return SNs


def getPmgr(objType, hutch, verbose):
    """ Returns a pmgr obj for the inputted hutch and objType """
    try:
        pmgr = pmgrobj(objType, hutch.lower())  # Launch pmgr instance
        pmgr.updateTables()                     # And update
        if verbose: print "Pmgr instance initialized for hutch: {0}".format(hutch.upper())
    except:
        print "Failed to create pmgr instance for hutch: {0}".format(hutch.upper())
        pmgr = None
    return pmgr

def printDiff(pmgr, objOld, cfgOld, objNew, cfgNew, verbose, **kwargs):
    """ Prints the diffs between the old values and new values"""
    name1 = kwargs.get("name1", "Old")
    name2 = kwargs.get("name2", "New")
    if verbose:
        print "{0}:".format(name1)
        pprint(objOld)
        pprint(cfgOld)
        
        print "\n{0}:".format(name2)
        pprint(objNew)
        pprint(cfgNew)

    diffs = {}
    ndiffs = 0

    for field in cfgOld.keys():
        try:
            if str(cfgNew[field]) != str(cfgOld[field]):
                diffs[field] = "{0}: {1: <20}  {2}: {3: <20}".format(
                    name1, cfgNew[field], name2, cfgOld[field])
                ndiffs += 1
        except: pass

    for field in objOld.keys():
        try:
            if str(objNew[field]) != str(objOld[field]) and field not in fields.keys():
                diffs[field] = "{0}: {1: <20}  {2}: {3: <20}".format(
                    name1, objNew[field], name2, objOld[field])
                ndiffs += 1
        except: pass

    print "\nNumber of diffs: {0}".format(ndiffs)
    if ndiffs > 0:
        for fld in diffs.keys():
            print "  {0: <15}: {1}".format(fld, diffs[fld])

def getAndSetConfig(PV, pmgr, objID, objDict, cfgDict, zenity=False):
    """ Creates a new config and then sets it to the objID """
    status = False
    # Get a valid cfg name
    cfgName = nextCfgName(pmgr, objDict["name"])
    cfgDict["name"] = cfgName
    cfgDict["FLD_TYPE"] = "{0}_{1}".format(cfgName, PV[:4])

    # # Create new cfg
    cfgID = newConfig(pmgr, cfgDict, cfgDict["name"])

    if not cfgID: 
        print "Failed to create cfg for {0}".format(cfgName)
        if zenity: system("zenity --error --text='Error: Failed to create new config'")
        return status

    # # Set obj to use cfg
    status = setObjCfg(pmgr, objID, cfgID)
    return status

def getMostRecentObj(hutches, SN, objType, verbose, zenity=False):
    """ 
    Finds all saved objs in all the pmgr instances for the SN inputted and 
    returns the most recently updated one along with the corresponding pmgr
    instance.
    """
    objs = {}
    for hutch in hutches:
        pmgr = getPmgr(objType, hutch, verbose)
        if not pmgr: continue

        if verbose: print "Checking pmgr SNs for this motor"
        objID = getObjWithSN(pmgr, SN, verbose)
        if not objID:
            print "Serial number {0} not found in {1} pmgr".format(SN,hutch.upper())
            continue
        time_Updated = pmgr.cfgs[pmgr.objs[objID]['config']]['dt_updated']
        if verbose: 
            print "Motor found"
            print "Last motor update done on {0}".format(time_Updated)
        objs[time_Updated] = [objID, hutch]

    # Make sure there is at least one obj with the corresponding SN
    if len(objs) == 0:
        print "Failed to apply: Serial number {0} not found in pmgr".format(SN)
        if zenity: system("zenity --error --text='Error: Motor not in pmgr'")
        return None, None

    # Use the most recent obj and the corresponding pmgr instance
    mostRecent = max(objs.keys())
    objID = objs[mostRecent][0]
    print "Using most recent obj saved on {0} from {1} pmgr".format(mostRecent, 
                                                                    objs[mostRecent][1])
    pmgr = getPmgr(objType, objs[mostRecent][1], verbose)
    
    return objID, pmgr

def getBasePV(PVArguments):
	"""
	Returns the first base PV found in the list of PVArguments. It looks for the 
	first colon starting from the right and then returns the string up until
	the colon. Takes as input a string or a list of strings.
	"""
	if type(PVArguments) != list:
		PVArguments = [PVArguments]
	for arg in PVArguments:
		if ':' not in arg: continue
		for i, char in enumerate(arg[::-1]):
			if char == ':':
				return arg[:-i]
	return None

# Functions pulled from Zack's utils.py file
# Original: /reg/neh/home/zlentz/python/pmgrPython/utils.py
import time
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print "{0} function took {1:0.3f} s".format(f.func_name, time2-time1)
        return ret
    return wrap

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
    pprint(obj)
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
    name = incrementMatching(name, allNames, maxLength=maxLenName)
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
    try:
        pmgr.applyConfig(objID)
        return True
    except Exception:
        return False

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

