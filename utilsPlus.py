# An Extension of utils to provide lower and mid level functions surrounding 
# pmgr objs

import psp.Pv as pv
import pyUtils as putl                
from caget import caget
from pprint import pprint
from pmgrobj import pmgrobj

### Higher Level Functions

Hutches = ["amo", "sxr", "mec", "cxi", "tst", "xcs", "xpp"]

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

