# An Extension of utils to provide lower and mid level functions surrounding 
# pmgr objs

import psp.Pv as pv
import pyUtils as putl
import logging
import subprocess
import os
import string
                
from caget import caget
from pprint import pprint
from pmgrobj import pmgrobj
from os import system


logger = logging.getLogger(__name__)

# Globals

Hutches = ["amo", "sxr", "mec", "cxi", "tst", "xcs", "xpp"]

supportedHutches = ['sxr','amo','sxd']    # Hutches currently supported.
# Add hutch names to this list for pmgr functionality. 
# Note: for the hutch to work, it must already be in the pmgr.

supportedObjTypes = ['ims_motor']         # ObjTypes currently supported.
# Add objtypes to this list for pmgr functionality. 
# This list is intended to allow for the script to handle newer objtypes as the
# pmgr becomes gets used for more devices.

nTries = 3                                # Number of attempts when using caget

def getCfgVals(pmgr, PV):
	""" Returns a dictionary of the live cfg fields associated with a PV """
	PV = PV.upper()
	configFields = listCfgFields(pmgr)
	cfgDict = getFieldDict(pmgr, PV, configFields)

	name = None

	try:
		name = caget(PV +".DESC")
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
	objDict = checkSNLength(objDict)

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
		parent = putl.getHutch(pmgr).upper()
	if type(parent) == str:
		parent = putl.cfgFromName(pmgr, parent)
	if not owner:
		owner = putl.getHutch(pmgr)
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
	name = putl.incrementMatching(str(name), allNames)
	return str(name)

def nextCfgName(pmgr, name):

	""" 
	Wrapper function for nextName that just makes sure the name is of type str
	"""
	allNames = putl.allCfgNames(pmgr)
	name = putl.incrementMatching(str(name), allNames,  maxLength=15)
	return str(name)

def objUpdate(pmgr, idx, objDict):
	""" Updates the obj using the fields specified in objDict """
	obj = pmgr.objs[idx]
	for field in objDict.keys():
		try: obj[field] = objDict[field]
		except: continue
	return putl.transaction(pmgr, "objectChange", idx, obj)


def get_motor_PVs(partialPV):
    motorPVs = []
    i = 1

    while i != 40:
        basePV = "%s:%02d"%(partialPV, i)
        print basePV
        
        try:
	        SN = caget(basePV + ".SN")
	        
	        if len(SN) >= 8:
		        motor_PVs[sn] = basepv
                print "PV: {0} is active".format(basePV)
                motorPVs += basePV
        except: pass
            
    return motorPVs


### Mid level functions

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

def getObjWithSN(pmgr, SN):
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
 			print "\nThe SN for motor {0} has an incorrect length. Adding zeros\
 to ensure proper pmgr functionality.".format(pmgr.objs[objID]["name"])
 			obj = pmgr.objs[objID]
 			obj["FLD_SN"] = pmgrSN
 			putl.transaction(pmgr, "objectChange", objID, obj)

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
		  
### Lower Level Functions

def checkSNLength(cfgDict):
	""" 
	Function that checks to make sure the SN in the configuration dictionary is
	9 digits long. Issues have come up becasue leading zeros get dropped 
	somewhere along the pipeline. It will return a corrected configuration 
	dictionary if the SN length is wrong, and return the same one if it is fine.
	"""

	# Make sure it is a string
	cfgDict["FLD_SN"] = str(cfgDict["FLD_SN"])

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
	return putl.listFieldsWith(pmgr, "obj", True)

def listCfgFields(pmgr):
	return putl.listFieldsWith(pmgr, "obj", False)


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


def getFieldDict(cfgPath):
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
		print "\nLive cfg values for {0}".format(caget(PV+".DESC"))
		pprint(objDict)
		pprint(cfgDict)

		print "\nPMGR cfg values for {0} before update".format(caget(PV+".DESC"))
		pprint(objOld)
		pprint(cfgOld)
		print

	cfgDict["FLD_TYPE"] = pmgr.cfgs[cfgID]["FLD_TYPE"]

	# Though this will ensure cfg Naming needs to be smarter
	# cfgDict["name"] = cfgOld["name"]

	if cfgOld["name"] in allNames: allNames.remove(cfgOld["name"])
	cfgDict["name"] = putl.incrementMatching(cfgDict["name"],
	                                         allNames,
	                                         maxLength=15)
	print "Saving configuration..." 
	# # Actually do the update
	didWork = putl.cfgChange(pmgr, cfgID, cfgDict)

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
	if not hutches: return hutches, objType, pmgr, SN
	if verbose: 
		print "Hutches: {0}".format(hutches)

	# Check for valid obj entry. Pmgr only supports ims motors as of 1/1/2016
	if objType in supportedObjTypes: pass
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
				SN[motorPV] = caget(motorPV + ".SN")
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
			PN = caget(PV + ".PN")
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

def printDiff(pmgr, objOld, cfgOld, objNew, cfgNew, verbose):
	""" Prints the diffs between the old values and new values"""

	if verbose:
		print "Old values:"
		pprint(objOld)
		pprint(cfgOld)
		
		print "\nNew values:"
		pprint(objNew)
		pprint(cfgNew)

	diffs = {}
	ndiffs = 0

	for field in cfgOld.keys():
		try:
			if str(cfgNew[field]) != str(cfgOld[field]):
				diffs[field] = "New: {0}, Old: {1}".format(
					cfgNew[field],
				    cfgOld[field])
				ndiffs += 1
		except: pass

	for field in objOld.keys():
		try:
			if str(objNew[field]) != str(objOld[field]):
				diffs[field] = "New: {0}, Old: {1}".format(
					objNew[field],
				    objOld[field])
				ndiffs += 1
		except: pass

	print "\nNumber of diffs: {0}".format(ndiffs)
	if ndiffs > 0:
		print "Diffs:"
		pprint(diffs)
		print

