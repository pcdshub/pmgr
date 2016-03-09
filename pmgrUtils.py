"""
pmgrUtils

Usage:
    pmgrUtils.py (save | apply | dmapply | import | diff) <PV>...
    pmgrUtils.py save <PV>... [--hutch=H] [-v|--verbose] [-z|--zenity]
    pmgrUtils.py apply <PV>... [--hutch=H] [-v|--verbose] [-z|--zenity]
    pmgrUtils.py dmapply <PV>... [--hutch=H] [-v|--verbose] [-z|--zenity]
    pmgrUtils.py import [<hutch>] [--hutch=H] [-u|--update] [-v|--verbose] [-z|--zenity] [--path=p]
    pmgrUtils.py diff <PV>... [--hutch=H] [-v|--verbose] [-z|--zenity]
    pmgrUtils.py [-h | --help]

Arguments
    <PV>          Motor PV(s). To do multiple motors, input the full PV as the
                  first argument, and then the numbers of the rest as single
                  entries, or in a range using a hyphen. An example would be the
                  following: 

                      python pmgrUtils.py save SXR:EXP:MMS:01-05 10 12 14-16

                  This will apply the save function to motors 01, 02, 03, 04, 05
                  10, 12, 14, 15 and 16.
    [<hutch>]     Hutch folder the function will import from. Ex. sxr will 
                  import from /reg/neh/operator/sxropr/device_config/ims/

Commands:
    save          Save live motor configuration
    apply         Apply the saved motor configuration to live values
    dmapply       Run dumb motor apply routine
    import        Imports configuration files from the <hutch>opr ims folder
    diff          Prints differences between pmgr and live values

Options:
    -h|--help     Show this help message
    -v|--verbose  Print more info on active process
    --hutch=H     Save or apply the config using the pmgr of the specified 
                  hutch. Valid entries are specified by the supportedHutches
                  variable. Can handle multiple comma-separated hutch inputs. 
                  Will save and import into all inputted hutches, and will apply
                  from the most recently updated pmgr. 
                  Currently supported hutches: ['sxr', 'amo', 'sxd']
    -u|--update   When importing, if serial number is already in the pmgr, the
                  config is overwitten by the one in the ims folder.
    -z|--zenity   Enables zenity pop-up boxes indicating when routines have 
                  errors and when they have completed
    --path=p      If path is specified when using import, the inputted path will
                  be used instead of the default paths to opr ims directories


"""
# Commented out zero functionality
    # --zero        Moves the motor to the zero position. If used with save, it is
    #               done before saving, for apply it is done after.

import pyUtils as putl
import utilsPlus as utlp
import datetime
import logging
import subprocess
import os
import string

from caget import caget
from pmgrobj import pmgrobj 
from pprint import pprint
from os import system
from docopt import docopt
from sys import exit
# from sxr_common.epics_ims_motor import epics_ims_motor

# Globals

supportedHutches = ['sxr','amo','sxd']    # Hutches currently supported.
# Add hutch names to this list for pmgr functionality. 
# Note: for the hutch to work, it must already be in the pmgr.

supportedObjTypes = ['ims_motor']         # ObjTypes currently supported.
# Add objtypes to this list for pmgr functionality. 
# This list is intended to allow for the script to handle newer objtypes as the
# pmgr becomes gets used for more devices.

nTries = 3                                # Number of attempts when using caget

logger = logging.getLogger(__name__)

def saveConfig(PV, hutch, pmgr, SN, verbose, zenity):
	"""
	Searches for the SN of the PV and then saves the live configuration values
	to the pmgr. 

	It will update the fields if the motor and configuration is already in the 
	pmgr. It will create new motor and config objects if either is not found and
	make the correct links between them.
	
	If a hutch is specified, the function will save the motor obj and cfg to the
	pmgr of that hutch. Otherwise it will save to the hutch listed on the PV.

	Currently only supports sxr and amo.
	"""

	print "Saving motor info to {0} pmgr".format(hutch.upper())

	# Grab motor information and configuration
	cfgDict = utlp.getCfgVals(pmgr, PV)
	objDict = utlp.getObjVals(pmgr, PV)
	allNames = putl.allCfgNames(pmgr)

	# Look through pmgr objs for a motor with that id
	if verbose: 
		print "Checking {0} pmgr SNs for this motor".format(hutch.upper())
	objID = utlp.getObjWithSN(pmgr, objDict["FLD_SN"])
	# Returns none if SN not there
	if verbose: 
		print "ObjID obtained from {0} pmgr: {1}".format(hutch.upper(), objID)


	# Update obj fields - create a new one if it doesnt exist
	if objID: 
		print "Saving motor information..."
		utlp.objUpdate(pmgr, objID, objDict)
		if verbose: print "\nMotor SN found in {0} pmgr, motor information \
updated".format(hutch.upper())

	else:
		print "\nSN {0} not found in pmgr, adding new motor obj...".format(SN)
		# Obj Name Check
		objDict["name"] = utlp.nextObjName(pmgr, objDict["name"])

		# # Create new obj
		objID = utlp.newObject(pmgr, objDict)
		if not objID:
			print "Failed to create obj for {0}".format(objDict["name"])
			if zenity:
				system("zenity --error --text='Error: Failed to create new \
object for {0} pmgr'".format(hutch.upper()))
			return

	# Get the cfg id the obj uses
	try:
		cfgID = pmgr.objs[objID]["config"]
	except: cfgID = None


	# Update the cfg fields
	if cfgID and pmgr.cfgs[cfgID]["name"].upper() != hutch.upper():
		# Update the existing cfg using the new values
		didWork, objOld, cfgOld = updateConfig(PV, pmgr, objID, cfgID, objDict, 
		                                       cfgDict, allNames, verbose)

		if not didWork:
			print "Failed to update the cfg with new values"
			if zenity: 
				system("zenity --error --text='Error: Failed to update config'")
			return

	# Else create a new configuration if not present and set it to the objID
	else:
		print "\nInvalid config associated with motor {0}. Adding new config.".format(SN)

		# Get a valid cfg name
		cfgName = utlp.nextCfgName(pmgr, cfgDict["name"])
		cfgDict["name"] = cfgName
		cfgDict["FLD_TYPE"] = "{0}_{1}".format(cfgName, PV[:4])

		# # Create new cfg
		cfgID = putl.newConfig(pmgr, cfgDict, cfgDict["name"])

		if not cfgID: 
			print "Failed to create cfg for {0}".format(cfgName)
			if zenity: system("zenity --error --text='Error: Failed to create new config'")
			return

		# # Set obj to use cfg
		status = False
		status = putl.setObjCfg(pmgr, objID, cfgID)
		if status:
			print "Motor '{0}' successfully added to pmgr".format(
				objDict["name"])
		else: 
			print "Motor '{0}' failed to be added to pmgr".format(objDict["name"])
			return

	pmgr.updateTables()
	print "\nSuccessfully saved motor info and configuration into {0} pmgr".format(hutch)


	# # Printing Diffs 
	cfgPmgr = pmgr.cfgs[cfgID]
	objPmgr = pmgr.objs[objID]

	printDiff(pmgr, objOld, cfgOld, objPmgr, cfgPmgr, verbose)


	if zenity: system('zenity --info --text="Motor configuration successfully \
saved into {0} pmgr"'.format(hutch.upper()))
		

			
def applyConfig(PV, hutches, SN, verbose, zenity):
	"""
	Searches the pmgr for the correct SN and then applies the configuration
	currently associated with that motor.
	
	If it fails to find either a SN or a configuration it will exit.
	"""
	
	if verbose: print "Getting most recently updated obj\n"
	# Find the most recently updated motor configuration from the hutches
	objs = {}
	for hutch in hutches:
		pmgr = getPmgr(objType, hutch, verbose)
		if not pmgr: continue

		if verbose: print "Checking pmgr SNs for this motor"
		objID = utlp.getObjWithSN(pmgr, SN)
		if not objID:
			print "Serial number {0} not found in {1} pmgr".format(SN, 
			                                                       hutch.upper())
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
		return

	# Use the most recent obj and the corresponding pmgr instance
	mostRecent = max(objs.keys())
	objID = objs[mostRecent][0]
	print "Using most recent obj saved on {0} from {1} pmgr".format(mostRecent, 
	                                                                objs[mostRecent][1])
	pmgr = getPmgr(objType, objs[mostRecent][1], verbose)
	if not pmgr: return

	# # Work-around for applyConfig
	# # applyObject uses the rec_base field of the obj to apply the PV values
	# # so for it to work properly we have to set rec_base to the correct 
	# # PV value associated with that motor at the moment
	
	# Change rec_base to the base PV and the port to the current port
	obj = pmgr.objs[objID]
	obj["rec_base"] = PV
	obj["FLD_PORT"] = caget(PV + ".PORT")
	putl.transaction(pmgr, "objectChange", objID, obj)

	# if verbose: 
	# 	cfgOld = utlp.getCfgVals(pmgr, PV)
	# 	print "\nLive cfg values for {0} before update".format(caget(PV+".DESC"))
	# 	pprint(cfgOld)

	# 	pmgrCfg = pmgr.cfgs[pmgr.objs[objID]["config"]]
	# 	print "\nPMGR cfg values for {0}".format(caget(PV+".DESC"))
	# 	pprint(pmgrCfg)
	# 	print

	cfgOld = utlp.getCfgVals(pmgr, PV)
	objOld = utlp.getObjVals(pmgr, PV)


	print "Applying configuration, please wait..."
	status = False
	status = putl.objApply(pmgr, objID)
	if not status:
		print "Failed to apply: pmgr transaction failure"
		if zenity: 
			system("zenity --error --text='Error: pmgr transaction failure'")
		return

	if verbose:
		cfgDict = utlp.getCfgVals(pmgr, PV)
		print "\nLive cfg values for {0} after update".format(caget(PV+".DESC"))
		pprint(cfgDict)
		print 

	print "Successfully completed apply"

	cfgNew = utlp.getCfgVals(pmgr, PV)
	objNew = utlp.getObjVals(pmgr, PV)

	printDiff(pmgr, objOld, cfgOld, objNew, cfgNew, verbose)

	if zenity:
		system('zenity --info --text="Configuration successfully applied"')



# This routine has not been tested yet 2/18/16
def dumbMotorApply(PV, hutches, SN, verbose, zenity):
	"""
	Routine used to handle dumb motors.

	Will open a terminal and prompt the user for a configuration name and then
	once a valid config is selected it will apply it.
	"""

	if verbose: print "Getting most recently updated obj"
	# Find the most recently updated motor configuration from the hutches
	objs = {}
	dates = []
	for hutch, pmgr in zip(hutches, pmgrs):
		if not verbose: print "\nChecking pmgr SNs for this motor"
		objID = utlp.getObjWithSN(pmgr, SN)
		if not objID:
			if verbose:
				print "Serial number {0} not found in {1} pmgr".format(
					SN, hutch.upper())
			continue
		objs[pmgr.objs[objID]['dt_updated']] = [objID, pmgr]

	# Make sure there is at least one obj with the corresponding SN
	if len(objs) == 0:
		print "Failed to apply: Serial number {0} not found in pmgr".format(SN)
		system("zenity --error --text='Error: Motor not in pmgr'")
		return

	# Use the most recent obj and the corresponding pmgr instance
	mostRecent = max(objs.keys())
	objID = objs[mostRecent][0]
	pmgr = objs[mostRecent][1]

	# Change rec_base to the base PV and port to the current port
	obj = pmgr.objs[objID]
	obj["rec_base"] = PV
	obj["FLD_PORT"] = caget(PV + ".PORT")
	putl.transaction(pmgr, "objectChange", objID, obj)


	# Get all the cfg names
	allNames = {}
	for pmgr in pmgrs:
	   names = putl.allCfgNames(pmgr)
	   for name in names: allNames[name] = pmgr

	pprint(allNames.keys())
	print "\nAbove is a list of all the valid configuration names in the \
inputted hutch(es)."
	
	confirm = "no"
	cfgName = None

	# Make sure the user inputs a correct configuration
 	while(confirm[:1].lower() != "y"):
		cfgName = input("Please input a correct configuration to apply\n")

		if cfgName.lower() not in allNames.keys():
			print "Invalid configuration inputted"
			continue

		confirm = input("\nAre you sure you want to apply {0}?\n".format(cfgName))

	print "Applying {0} to {1}..".format(cfgName, PV)
	pmgr = allNames[cfgName]              # What is happening here?
	cfgID = cfgFromName(pmgr, cfgName)    # Get cfgID from cfgName
	

	# Quick ID check
	if not cfgID:
		print "Error when getting config ID from name: {0}".format(config)
		if zenity: system("zenity --error --text='Error: Failed to get cfgID'")
		return

	# Set the cfg to the motor object
	status = False
	status = putl.setObjCfg(pmgr, objID, cfgID)
	if not status:
		print "Failed apply cfg to object"
		if zenity: system("zenity --error --text='Error: Failed to set cfgID \
to object'")
		return
	
	# Actually do the update
	status = False
	status = putl.objApply(pmgr, objID)
	if not status:
		print "Failed to apply: pmgr transaction failure"
		if zenity: system("zenity --error --text='Error: pmgr transaction \
failure'")
		return
	
	print "Successfully completed apply"
	if zenity: system('zenity --info --text="Configuration successfully applied"')



def importConfigs(hutch, pmgr, path, update = False, verbose = False):
    """
    Imports all the configurations in the default directory for configs for the 
    given hutch as long as there is a serial number given in the config file.

    It first creates a dictionary of serial numbers to config paths, omitting 
    all configs that do not have a serial number. It then loops through each
    path, creating a field dictionary from the configs and then performs checks
    to determine if the motor should be added as a new motor, have its fields
    updated, or skipped.

    """

    allNames = putl.allCfgNames(pmgr)
    if verbose: print "Creating motor DB"
    old_cfg_paths = createmotordb(hutch, path)

    pmgr_SNs = get_all_SN(pmgr)

    for motor in old_cfg_paths.keys():
        cfgDict = getFieldDict(old_cfg_paths[motor])
        objDict = getFieldDict(old_cfg_paths[motor])

        pmgr.updateTables()
        name = None

        if cfgDict["FLD_DESC"]:
            name = cfgDict["FLD_DESC"]
        elif cfgDict["FLD_SN"]:
            name = "SN:{0}".format(cfgDict["FLD_SN"])
        else:
            name = "Unknown"
		                               
        # Check if the serial number is already in the pmgr
        if str(cfgDict["FLD_SN"]) in pmgr_SNs:
            if verbose: print "\nMotor '{0}' already in pmgr".format(name)

            # Skip the motor if update is False
            if not update:
                if verbose: print "    Skipping motor"
                continue
        
            if verbose: print "    Updating motor fields"
            objID = putl.firstObjWith(pmgr, "FLD_SN", str(cfgDict["FLD_SN"]))
            utlp.objUpdate(pmgr, objID, objDict)

            cfgID = pmgr.objs[objID]["config"]
            if cfgID and pmgr.cfgs[cfgID]["name"] != hutch.upper():
                # cfgOld = pmgr.cfgs[cfgID]
                cfgDict["FLD_TYPE"] = pmgr.cfgs[cfgID]["FLD_TYPE"]
                cfgDict["name"] = putl.incrementMatching(str(name), 
                                                         allNames,  
                                                         maxLength=15)
                allNames.add(cfgDict["name"])

                didWork = putl.cfgChange(pmgr, cfgID, cfgDict)
                
                if verbose: 
	                if didWork: print "        Completed update"
	                else: print "        Failed to update the cfg with new values"
		
            continue
        

        try:
            # Create a unique name for the config and then add the new config
            cfgDict["name"] = utlp.nextCfgName(pmgr, name)
            CfgID = putl.newConfig(pmgr, cfgDict, cfgDict["name"])

            pmgr.updateTables()

            # Create a unique name for the obj and then add it
            objDict["name"] = utlp.nextObjName(pmgr, name)
            ObjID = utlp.newObject(pmgr, objDict)
        
            pmgr.updateTables()
            
            # Set the obj to use the cfg settings
            status = False            
            status = putl.setObjCfg(pmgr, ObjID, CfgID)
            
            if verbose:
	            if status: 
	                print "Motor '{0}' successfully added to pmgr".format(
	                    objDict["name"])
	            else: 
	                print "Motor '{0}' failed to be added to pmgr".format(
	                    objDict["name"])

        except:
	        if verbose:
		        print "Motor '{0}' failed to be added to pmgr".format(
			        objDict["name"])
	        continue


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

# def zero(motorPV, verbose = False):
# 	"""
# 	Function that will move a motor to the zero position. Useful only when you
# 	need to constantly reset a number of motors back to the zero position.
# 	"""
# 	try:
# 		SN = caget(motorPV + ".SN")
# 	except:
# 		print "Could not contact motor: {0}\nSkipping..".format(motorPV)
# 		return
	
# 	if verbose: print "Zeroing Motor: {0}".format(motorPV)
# 	motor = epics_ims_motor(motorPV)

# 	if verbose: print "Moving.."
# 	motor.mv(0)
# 	motor.wait_for_motion()
# 	if verbose: print "Move complete!"

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

def parsePVArguments(PVArguments):
	"""
	Parses PV input arguments and returns a set of motor PVs that will have
	the pmgrUtil functions applied to.
	"""
	motorPVs = set()
	basePV = PVArguments[0][:12]

	for arg in PVArguments:
		try:

			if '-' in arg:
				splitArgs = arg.split('-')

				if splitArgs[0][:-2] == basePV: motorPVs.add(splitArgs[0])

				start = int(splitArgs[0][-2:])
				end = int(splitArgs[1])

				while start <= end:
					motorPVs.add(basePV + "%02d"%start)
					start += 1
 
			elif len(arg) > 3:
				if arg[:-2] == basePV: motorPVs.add(arg)
			
			elif len(arg) < 3:
				motorPVs.add(basePV + "%02d"%int(arg))
			
			else: pass
				
		except: pass
			
	motorPVs = list(motorPVs)
	motorPVs.sort()
	return motorPVs

def Diff(PV, hutch, pmgr, SN, verbose):
	""" 
	Prints the differences between the live values and the values saved in the
	pmgr.
	"""

	cfgLive = utlp.getCfgVals(pmgr, PV)
	objLive = utlp.getObjVals(pmgr, PV)

	# Look through pmgr objs for a motor with that SN
	if verbose: 
		print "Checking {0} pmgr SNs for this motor".format(hutch.upper())
	objID = utlp.getObjWithSN(pmgr, objLive["FLD_SN"])

	if not objID:
		print "\nSN {0} not found in pmgr, cannot find diffs".format(SN)
		return
	
	try: cfgID = pmgr.objs[objID]["config"]
	except: cfgID = None
	
	if not cfgID:
		print "\nInvalid config associated with motor, cannot find diffs".format(SN)
		return

	cfgPmgr = pmgr.cfgs[cfgID]
	objPmgr = pmgr.objs[objID]

	printDiff(pmgr, objLive, cfgLive, objPmgr, cfgPmgr, verbose) 

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
	
###############################################################################
## 					   	 		     Main									 ## 
###############################################################################


if __name__ == "__main__":
	arguments = docopt(__doc__)
	PVArguments = arguments["<PV>"]
	if arguments["--path"]: path = arguments["--path"]
	else: path = []
	if arguments["--verbose"] or arguments["-v"]: verbose = True
	else: verbose = False
	if arguments["--zenity"] or arguments["-z"]: zenity = True
	else: zenity = False
	if arguments["--update"] or arguments["-u"]: update = True
	else: update = False
	if arguments["--hutch"]: 
		hutches = [hutch.lower() for hutch in arguments["--hutch"].split(',')]
	else: hutches = []
	if arguments["<hutch>"]:
		hutchPaths = [hutch.lower() for hutch in arguments["<hutch>"].split(',')]
	elif len(path) > 0:  hutchPaths = ['sxd']
	else: hutchpath = []

	# Try import first
	if arguments["import"]:
		hutches = motorPrelimChecks(hutchPaths, hutches, None, verbose)[0]
		hutchPaths = motorPrelimChecks(hutchPaths, hutchPaths, None, verbose)[0]
		
		for hutchPath in hutchPaths:
			for hutch in hutches:
				pmgr = getPmgr(objType, hutch, verbose)
				if not pmgr: continue

				print "Importing configs from {0}opr into {1} pmgr".format(
					hutchPath, hutch)
				importConfigs(hutchPath, pmgr, path, update, verbose)
			
			if path: break
		exit()
		
	# Make sure PVs are inputted
	# Not working properly when usng more that one input!!!
	if len(PVArguments) > 0: motorPVs = parsePVArguments(PVArguments)
	else:
		if zenity: system("zenity --error --text='No PV inputted'")
		exit("No PV inputted.")

	# Prelimenary Checks
	if verbose: print "\nPerforming preliminary checks for pmgr paramters\n"
	if arguments["--hutch"]: 
		hutches = [hutch.lower() for hutch in arguments["--hutch"].split(',')]
	else: hutches = []
	hutches, objType, SNs = motorPrelimChecks(motorPVs, hutches, None, verbose)
	if not hutches or not objType or not SNs:
	    if zenity: system("zenity --error --text='Failed prelimenary checks'")
	    exit("\nFailed prelimenary checks\n")

	# Loop through each of the motorPVs
	for PV in motorPVs:
		print "Motor PV: {0}".format(PV)
		m_DESC = caget(PV + ".DESC")
		print "Motor description: {0}".format(m_DESC)
		if not SNs[PV]: continue
		else: SN = SNs[PV]
		print "Motor SN: {0}\n".format(SN)



		# Start with the two applies first.
		# Apply and make sure it is a smart motor
		if arguments["apply"]:
			if not dumbMotorCheck(PV):
				applyConfig(PV, hutches, SN, verbose, zenity)
			else:
				print "Motor connected to PV:{0} is a dumb motor, must use \
dmapply\n".format(PV)
				if zenity:
					system("zenity --error --text='Error: Dumb motor detected'")

		# Apply routine for dumb motors
		elif arguments["dmapply"]:
			if dumbMotorCheck(PV):
				dumbMotorApply(PV, hutch, pmgr, SN, verbose, zenity)
			else:
				print "Motor connected to PV:{0} is a smart motor, must use \
apply\n".format(PV)
				if zenity:
					system("zenity --error --text='Error: Smart motor detected'")

		# # Check if the user asked to zero the motor
		# if arguments["--zero"]:
		# 	print "Moving motor {0} to zero position".format(PV)
		# 	zero(PV, verbose)
		
		# If either apply or dmapply was invoked do not check for save or import
		if arguments["apply"] or arguments["dmapply"]: continue


		for hutch in hutches:
			pmgr = getPmgr(objType, hutch, verbose)
			if not pmgr: continue

			if arguments["diff"]:
				Diff(PV, hutch, pmgr, SN, verbose)
				continue

			if arguments["save"]:
				saveConfig(PV, hutch, pmgr, SN, verbose, zenity)
				continue
