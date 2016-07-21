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
    [<hutch>]     Hutch opr folder the function will import cfgs from. For 
                  example, sxr will import from 

                      /reg/neh/operator/sxropr/device_config/ims/

Commands:
    save          Save live motor configuration
    apply         Apply the saved motor configuration to live values
    dmapply       Run dumb motor apply routine
    import        Imports configuration files from the <hutch>opr ims folder
    diff          Prints differences between pmgr and live values

Options:
    --hutch=H     Save or apply the config using the pmgr of the specified 
                  hutch. Valid entries are specified by the supportedHutches
                  variable. Can handle multiple comma-separated hutch inputs. 
                  Will save and import into all inputted hutches, and will apply
                  from the most recently updated pmgr. 
    -u|--update   When importing, if serial number is already in the pmgr, the
                  config is overwitten by the one in the ims folder.
    --path=p      If path is specified when using import, the inputted path is 
                  where the function will import cfgs from instead of the opr
                  locations.
    -v|--verbose  Print more info on active process
    -z|--zenity   Enables zenity pop-up boxes indicating when routines have 
                  errors and when they have completed.
    -h|--help     Show this help message

pmgrUtils allows certain parameter manager transactions to be done using the
command line. Fundamentally, it will perform these transactions on motors using
their individual serial numbers allowing the same motor can be plugged into
any digi port and the script will push the same configuration into that motor.
Conversely, motor configurations can also be saved from any port.

Hutches that are supported are listed in the pmgrUtils.cfg file. Adding a hutch
to the list of hutches there should enable pmgrUtils support for that hutch (so
long as it is already in the pmgr).
"""

import utilsPlus as utlp
import psp.Pv as pv
from pprint import pprint
from os import system
from docopt import docopt
from sys import exit
from difflib import get_close_matches
# from optparse import OptionParser

def saveConfig(PV, hutch, pmgr, SN, verbose, zenity):
    """
    Searches for the SN of the PV and then saves the live configuration values
    to the pmgr. 

    It will update the fields if the motor and configuration is already in the 
    pmgr. It will create new motor and config objects if either is not found and
    make the correct links between them.
    
    If a hutch is specified, the function will save the motor obj and cfg to the
    pmgr of that hutch. Otherwise it will save to the hutch listed on the PV.
    """
    print "Saving motor info to {0} pmgr".format(hutch.upper())
    # Grab motor information and configuration
    cfgDict = utlp.getCfgVals(pmgr, PV)
    objDict = utlp.getObjVals(pmgr, PV)
    allNames = utlp.allCfgNames(pmgr)

    # Look through pmgr objs for a motor with that id
    if verbose: print "Checking {0} pmgr SNs for this motor".format(hutch.upper())
    objID = utlp.getObjWithSN(pmgr, objDict["FLD_SN"], verbose)
    if verbose: print "ObjID obtained from {0} pmgr: {1}".format(hutch.upper(), objID)

    # If an objID was found, update the obj
    if objID: 
        print "Saving motor information..."
        utlp.objUpdate(pmgr, objID, objDict)
        if verbose: print "\nMotor SN found in {0} pmgr, motor information \
updated".format(hutch.upper())
    # Else try to create a new obj
    else:
        print "\nSN {0} not found in pmgr, adding new motor obj...".format(SN)
        # Name availability check
        objDict["name"] = utlp.nextObjName(pmgr, objDict["name"])
        # Create new obj
        objID = utlp.newObject(pmgr, objDict)
        if not objID:
            print "Failed to create obj for {0}".format(objDict["name"])
            if zenity:
                system("zenity --error --text='Error: Failed to create new \
object for {0} pmgr'".format(hutch.upper()))
            return 

    # Try to get the cfg id the obj uses
    try: cfgID = pmgr.objs[objID]["config"]
    except: cfgID = None

    # If there was a valid cfgID and it isnt the default one, try to update the cfg
    if cfgID and pmgr.cfgs[cfgID]["name"].upper() != hutch.upper():
        didWork, objOld, cfgOld = utlp.updateConfig(PV, pmgr, objID, cfgID, objDict, 
                                                    cfgDict, allNames, verbose)
        if not didWork:
            print "Failed to update the cfg with new values"
            if zenity: 
                system("zenity --error --text='Error: Failed to update config'")
            return
    # Else create a new configuration and try to set it to the objID
    else:
        print "\nInvalid config associated with motor {0}. Adding new config.".format(SN)
        status = utlp.getAndSetConfig(PV, pmgr, objID, objDict, cfgDict)
        if not status:
            print "Motor '{0}' failed to be added to pmgr".format(objDict["name"])
            return 
        print "Motor '{0}' successfully added to pmgr".format(objDict["name"])

    pmgr.updateTables()
    # Change the config and object names to be the motor description
    obj = pmgr.objs[objID]
    cfg = pmgr.cfgs[obj["config"]]
    obj["name"] = utlp.nextObjName(pmgr, obj["FLD_DESC"])
    cfg["name"] = utlp.nextCfgName(pmgr, obj["FLD_DESC"])
    utlp.transaction(pmgr, "objectChange", objID, obj)
    utlp.transaction(pmgr, "configChange", cfgID, cfg)
    
    print "\nSuccessfully saved motor info and configuration into {0} pmgr".format(hutch)
    # Try to print the diffs
    if cfgID and objID:
	    cfgPmgr = pmgr.cfgs[cfgID]
	    objPmgr = pmgr.objs[objID]
	    try: utlp.printDiff(pmgr, objOld, cfgOld, objPmgr, cfgPmgr, verbose)
	    except: pass
	    if zenity: system('zenity --info --text="Motor configuration \
successfully saved into {0} pmgr"'.format(hutch.upper()))

def applyConfig(PV, hutches, objType, SN, verbose, zenity, dumb=False, 
                dumb_cfg=None, dumb_confirm=True):
    """
    Searches the pmgr for the correct SN and then applies the configuration
    currently associated with that motor.
    
    If it fails to find either a SN or a configuration it will exit.
    """
    # Find the most recently updated obj in the pmgrs of each hutch inputted
    if verbose: print "Getting most recently updated obj\n"
    objID, pmgr = utlp.getMostRecentObj(hutches, SN, objType, verbose)
    if not objID or not pmgr: return

    # # Work-around for applyConfig
    # # applyObject uses the rec_base field of the obj to apply the PV values
    # # so for it to work properly we have to set rec_base to the correct 
    # # PV value associated with that motor at the moment
    # Change rec_base field to the base PV and the port field to the live port
    obj = pmgr.objs[objID]
    port = pv.get(PV + ".PORT")
    if obj["rec_base"] != PV or obj["FLD_PORT"] != port:
        obj["rec_base"] = PV
        obj["FLD_PORT"] = port
        utlp.transaction(pmgr, "objectChange", objID, obj)

    if dumb:
        # Get all the cfg names
        allNames = {}
        for hutch in hutches:
            pmgr = utlp.getPmgr(objType, hutch, verbose)
            names = utlp.allCfgNames(pmgr)
            for name in names: allNames[name] = hutch

        # Make sure the user inputs a correct configuration
        cfgName = dumb_cfg
        if dumb_confirm:
            confirm = "no"
            while(confirm[0].lower() != "y"):
                if cfgName is not None:
                    print "Closest matches to your input:"
                    closest_cfgs = get_close_matches(cfgName, allNames.keys(), 15, 0.1)
                    pprint(closest_cfgs)
                cfgName = raw_input("Please input a configuration to apply or search:\n")
                if cfgName not in allNames:
                    print "Invalid configuration inputted."
                    continue
                confirm = raw_input("\nAre you sure you want to apply {0} to {1}?\n".format(cfgName, PV))
        elif cfgName not in allNames:
            print "Invalid configuration {} chosen.".format(cfgName)
            return

        # Get the selected configuration's ID
        pmgr = utlp.getPmgr(objType, allNames[cfgName], verbose)
        cfgID = utlp.cfgFromName(pmgr, cfgName)
        if not cfgID:
            print "Error when getting config ID from name: {0}".format(cfgName)
            if zenity: system("zenity --error --text='Error: Failed to get cfgID'")
            return

        # Set configuration of dumb motor pmgr object
        if obj["config"] != cfgID:
            status = False
            status = utlp.setObjCfg(pmgr, objID, cfgID)
            if not status:
                print "Failed set cfg to object"
                if zenity: system("zenity --error --text='Error: Failed to set cfgID to object'")
                return

        # Set the obj name and desc to use the cfg name (only for dumb motors)
        obj["name"] = utlp.nextObjName(pmgr, pmgr.cfgs[cfgID]["name"])
        obj["FLD_DESC"] = pmgr.cfgs[cfgID]["name"]
        utlp.transaction(pmgr, "objectChange", objID, obj)

    # For future diff comparison
    cfgOld = utlp.getCfgVals(pmgr, PV)
    objOld = utlp.getObjVals(pmgr, PV)

    # Apply the pmgr configuration to the motor
    print "Applying configuration, please wait..."
    status = False
    status = utlp.objApply(pmgr, objID)
    if not status:
        print "Failed to apply: pmgr transaction failure"
        if zenity: 
            system("zenity --error --text='Error: pmgr transaction failure'")
        return
    print "Successfully completed apply"

    # Try to print the diffs
    cfgNew = utlp.getCfgVals(pmgr, PV)
    objNew = utlp.getObjVals(pmgr, PV)
    try: utlp.printDiff(pmgr, objOld, cfgOld, objNew, cfgNew, verbose)
    except: pass
    if zenity: system('zenity --info --text="Configuration successfully applied"')

def dumbMotorApply(PV, hutches, objType, SN, verbose, zenity):
    """
    Routine used to handle dumb motors.

    Will open a terminal and prompt the user for a configuration name and then
    once a valid config is selected it will apply it.
    """
    applyConfig(PV, hutches, objType, SN, verbose, zenity, dumb=True)

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
	if verbose: print "Creating motor DB"
	old_cfg_paths = utlp.createmotordb(hutch, path)
	pmgr_SNs = utlp.get_all_SN(pmgr)

	for motor in old_cfg_paths.keys():
		allNames = utlp.allCfgNames(pmgr)
		cfgDict = utlp.getImportFieldDict(old_cfg_paths[motor])
		objDict = utlp.getImportFieldDict(old_cfg_paths[motor])        
		if "MFI" in objDict["FLD_PN"]:
			dumb = True
		else: dumb = False 
		pmgr.updateTables()
		name = None
		if cfgDict["FLD_DESC"]:
			name = cfgDict["FLD_DESC"]
		elif cfgDict["FLD_SN"]:
			name = "SN:{0}".format(cfgDict["FLD_SN"])
		else:
			name = "Unknown"
		# Pad SN with zeros if necessary
		cfgDict = utlp.checkSNLength(cfgDict, pmgr)
		objDict = utlp.checkSNLength(objDict, pmgr)

		if dumb:
			if verbose: print "\nDumb motor PN found. Using config only"
			if name in allNames:
				if verbose: print "Config '{0}' already in pmgr".format(name)
				if not update:
					if verbose: print "    Skipping motor"
					continue
				if verbose: print "    Updating config fields"
				cfgID = utlp.cfgFromName(pmgr, name)
				error = utlp.cfgUpdate(pmgr, cfgID, cfgDict)
				if not error:
					print   "        Completed update"
				else: print "        Failed to update the cfg with new values"
			else:
				if verbose: print "Adding config '{0}' to pmgr".format(name)
				cfgID = utlp.newConfig(pmgr, cfgDict, cfgDict["FLD_DESC"])
				if cfgID is not None:
					print "Config '{0}' successfully added to pmgr".format(
						cfgDict["FLD_DESC"])
				else: 
					print "Config '{0}' failed to be added to pmgr".format(
						cfgDict["FLD_DESC"])
			pmgr.updateTables()
			continue	                

		# Check if the serial number is already in the pmgr
		if str(cfgDict["FLD_SN"]) in pmgr_SNs:
			if verbose: print "\nMotor '{0}' already in pmgr".format(name)
			# Skip the motor if update is False
			if not update:
				if verbose: print "    Skipping motor"
				continue
			if verbose: print "    Updating motor fields"
			objID = utlp.firstObjWith(pmgr, "FLD_SN", str(cfgDict["FLD_SN"]))
			utlp.objUpdate(pmgr, objID, objDict)
			cfgID = pmgr.objs[objID]["config"]
			if cfgID and pmgr.cfgs[cfgID]["name"] != hutch.upper():
				if cfgDict["FLD_DESC"] in allNames: allNames.remove(cfgDict["FLD_DESC"])
				cfgDict["FLD_TYPE"] = pmgr.cfgs[cfgID]["FLD_TYPE"]
				cfgDict["name"] = utlp.incrementMatching(str(name), 
														 allNames,  
														 maxLength=42)
				allNames.add(cfgDict["name"])
				# print "test"
				didWork = utlp.cfgChange(pmgr, cfgID, cfgDict)
				if verbose: 
					if didWork: print "        Completed update"
					else: print "        Failed to update the cfg with new values"
			continue

		# Add a new obj and set it to use the cfg
		try:
			# Create a unique name for the config and then add the new config
			cfgDict["name"] = utlp.nextCfgName(pmgr, name)
			cfgID = utlp.newConfig(pmgr, cfgDict, cfgDict["name"])
			pmgr.updateTables()
			# Create a unique name for the obj and then add it
			objDict["name"] = utlp.nextObjName(pmgr, name)
			ObjID = utlp.newObject(pmgr, objDict)
			pmgr.updateTables()
			# Set the obj to use the cfg settings
			status = False            
			status = utlp.setObjCfg(pmgr, ObjID, cfgID)
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

def Diff(PV, hutch, pmgr, SN, verbose):
    """ 
    Prints the differences between the live values and the values saved in the
    pmgr.
    """
    # Get live configuration
    cfgLive = utlp.getCfgVals(pmgr, PV)
    objLive = utlp.getObjVals(pmgr, PV)
    # Look through pmgr objs for a motor with that SN
    if verbose: 
        print "Checking {0} pmgr SNs for this motor".format(hutch.upper())
    objID = utlp.getObjWithSN(pmgr, objLive["FLD_SN"], verbose)
    if not objID:
        print "\nSN {0} not found in pmgr, cannot find diffs".format(SN)
        return
    try: cfgID = pmgr.objs[objID]["config"]
    except: cfgID = None
    if not cfgID:
        print "\nInvalid config associated with motor, cannot find diffs".format(SN)
        return
    # Get pmgr configurations
    cfgPmgr = pmgr.cfgs[cfgID]
    objPmgr = pmgr.objs[objID]
    # Print the diffs between the live and pmgr configs
    # Fix this so that it prints something sensible
    try: utlp.printDiff(pmgr, objLive, cfgLive, objPmgr, cfgPmgr, verbose, 
                        name1 = "Live", name2 = "Pmgr") 
    except: pass

def parsePVArguments(PVArguments):
	"""
	Parses PV input arguments and returns a set of motor PVs that will have
	the pmgrUtil functions applied to.
	"""
	PVs = set()
	if len(PVArguments) == 0: return None
	basePV = utlp.getBasePV(PVArguments)
	if not basePV: return None
	for arg in PVArguments:
		try:
			if '-' in arg:
				splitArgs = arg.split('-')
				if utlp.getBasePV(splitArgs[0]) == basePV: PVs.add(splitArgs[0])
				start = int(splitArgs[0][-2:])
				end = int(splitArgs[1])
				while start <= end:
					PVs.add(basePV + "{:02}".format(start))
					start += 1
			elif len(arg) > 3:
				if utlp.getBasePV(arg) == basePV: PVs.add(arg)
			elif len(arg) < 3:
				PVs.add(basePV + "{:02}".format(int(arg)))
			else: pass
		except: pass
	PVs = list(PVs)
	PVs.sort()
	return PVs

################################################################################
##                                   Main                                     ##
################################################################################

if __name__ == "__main__":
    # Parse docopt variables
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
    else: hutchPaths = []

    # Try import first
    if arguments["import"]:
        # A hack to get the appropriate hutch list and hutch path without 
        # rewriting any new functions. The logic is pretty ugly so it would be
        # nice to redo at some point.
        hutches, _, _ = utlp.motorPrelimChecks(hutchPaths, hutches, None, verbose)
        hutchPaths, _, _ = utlp.motorPrelimChecks(hutchPaths, hutchPaths, None, verbose)
        objType = "ims_motor"
        for hutchPath in hutchPaths:
            for hutch in hutches:
                pmgr = utlp.getPmgr(objType, hutch, verbose)
                if not pmgr: continue
                print "Importing configs from {0}opr into {1} pmgr".format(
                    hutchPath, hutch)
                importConfigs(hutchPath, pmgr, path, update, verbose)
            if path: break
        exit()                            # Do not continue
        
    # Parse the PV input into full PV names, exit if none inputted
    if len(PVArguments) > 0: motorPVs = parsePVArguments(PVArguments)
    else:
        if zenity: system("zenity --error --text='No PV inputted'")
        exit("No PV inputted.")

    # Run some prelimenary checks
    if verbose: print "\nPerforming preliminary checks for pmgr paramters\n"
    if arguments["--hutch"]: 
        hutches = [hutch.lower() for hutch in arguments["--hutch"].split(',')]
    else: hutches = []
    hutches, objType, SNs = utlp.motorPrelimChecks(motorPVs, hutches, None, verbose)
    if not hutches or not objType or not SNs:
        if zenity: system("zenity --error --text='Failed prelimenary checks'")
        exit("\nFailed prelimenary checks\n")

    # Loop through each of the motorPVs
    for PV in motorPVs:
        # Print some motor info
        print "Motor PV:          {0}".format(PV)
        m_DESC = pv.get(PV + ".DESC")
        print "Motor description: {0}".format(m_DESC)
        if not SNs[PV]:
            print "Could not get SN for motor: {0}.".format(m_DESC)
            print "Skipping motor.\n"
            continue
        SN = SNs[PV]
        if verbose: 
            print "Motor SN: {0}\n".format(SN)

        # If inputted apply, run apply routine and sure it is a smart motor
        if arguments["apply"]:
            if not utlp.dumbMotorCheck(PV):
                applyConfig(PV, hutches, objType, SN, verbose, zenity)
            else:
                print "Motor connected to PV:{0} is a dumb motor, must use \
dmapply\n".format(PV)
                if zenity:
                    system("zenity --error --text='Error: Dumb motor detected'")

        # Else if inputted dumb apply try apply routine for dumb motors
        elif arguments["dmapply"]:
            if utlp.dumbMotorCheck(PV):
                dumbMotorApply(PV, hutches, objType, SN, verbose, zenity)
            else:
                print "Motor connected to PV:{0} is a smart motor, must use \
apply\n".format(PV)
                if zenity:
                    system("zenity --error --text='Error: Smart motor detected'")
        
        # Else loop through the hutches and check for diff and save 
        else:
            for hutch in hutches:
                pmgr = utlp.getPmgr(objType, hutch, verbose)
                if not pmgr: continue
                if arguments["diff"]:
                    Diff(PV, hutch, pmgr, SN, verbose)
                    continue
                if arguments["save"]:
                    saveConfig(PV, hutch, pmgr, SN, verbose, zenity)
                    continue
