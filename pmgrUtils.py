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

from caget import caget
from pprint import pprint
from os import system
from docopt import docopt
from sys import exit

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
	allNames = utlp.allCfgNames(pmgr)


	# Look through pmgr objs for a motor with that id
	if verbose: print "Checking {0} pmgr SNs for this motor".format(hutch.upper())
	objID = utlp.getObjWithSN(pmgr, objDict["FLD_SN"]. verbose)
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
	print "\nSuccessfully saved motor info and configuration into {0} pmgr".format(hutch)


	# Try to print the diffs 
	cfgPmgr = pmgr.cfgs[cfgID]
	objPmgr = pmgr.objs[objID]
	try: utlp.printDiff(pmgr, objOld, cfgOld, objPmgr, cfgPmgr, verbose)
	except: pass

	if zenity: system('zenity --info --text="Motor configuration successfully \
saved into {0} pmgr"'.format(hutch.upper()))

		
			
def applyConfig(PV, hutches, objType, SN, verbose, zenity):
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
	obj["rec_base"] = PV
	obj["FLD_PORT"] = caget(PV + ".PORT")
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



# This routine has not been tested yet 2/18/16
def dumbMotorApply(PV, hutches, objType, SN, verbose, zenity):
	"""
	Routine used to handle dumb motors.

	Will open a terminal and prompt the user for a configuration name and then
	once a valid config is selected it will apply it.
	"""

	# Find the most recently updated obj in the pmgrs of each hutch inputted
	if verbose: print "Getting most recently updated obj\n"
	objID, pmgr = utlp.getMostRecentObj(hutches, SN, objType, verbose)
	if not objID or not pmgr: return

	
	# # Work-around for applyConfig
	# # applyObject uses the rec_base field of the obj to apply the PV values
	# # so for it to work properly we have to set rec_base to the correct 
	# # PV value associated with that motor at the moment

	# Change rec_base to the base PV and port to the current port
	obj = pmgr.objs[objID]
	obj["rec_base"] = PV
	obj["FLD_PORT"] = caget(PV + ".PORT")
	utlp.transaction(pmgr, "objectChange", objID, obj)


	# Get all the cfg names
	allNames = {}
	for hutch in hutches:
		pmgr = utlp.getPmgr(objType, hutch, verbose)
		names = utlp.allCfgNames(pmgr)
		for name in names: allNames[name] = hutch

	# Show the names to the user
	pprint(allNames.keys())
	print "\nAbove is a list of all the valid configuration names in the \
inputted hutch(es)."


	# Make sure the user inputs a correct configuration
	confirm = "no"
	cfgName = None
	
 	while(confirm[:1].lower() != "y"):
		cfgName = input("Please input a correct configuration to apply\n")

		if cfgName.lower() not in allNames.keys():
			print "Invalid configuration inputted"
			continue
		confirm = input("\nAre you sure you want to apply {0}?\n".format(cfgName))


	# Get the selected configuration's ID
	print "Applying {0} to {1}..".format(cfgName, PV)
	pmgr = utlp.getPmgr(objType, getallNames[cfgName], verbose)              
	cfgID = utlp.cfgFromName(pmgr, cfgName)
	if not cfgID:
		print "Error when getting config ID from name: {0}".format(cfgName)
		if zenity: system("zenity --error --text='Error: Failed to get cfgID'")
		return


	# Set the cfg to the motor object
	status = False
	status = utlp.setObjCfg(pmgr, objID, cfgID)
	if not status:
		print "Failed set cfg to object"
		if zenity: system("zenity --error --text='Error: Failed to set cfgID \
to object'")
		return
	

	# Apply the config
	status = False
	status = utlp.objApply(pmgr, objID)
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

    allNames = utlp.allCfgNames(pmgr)
    if verbose: print "Creating motor DB"
    old_cfg_paths = utlp.createmotordb(hutch, path)

    pmgr_SNs = utlp.get_all_SN(pmgr)

    for motor in old_cfg_paths.keys():
        cfgDict = utlp.getFieldDict(old_cfg_paths[motor])
        objDict = utlp.getFieldDict(old_cfg_paths[motor])

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
            objID = utlp.firstObjWith(pmgr, "FLD_SN", str(cfgDict["FLD_SN"]))
            utlp.objUpdate(pmgr, objID, objDict)

            cfgID = pmgr.objs[objID]["config"]
            if cfgID and pmgr.cfgs[cfgID]["name"] != hutch.upper():
                cfgDict["FLD_TYPE"] = pmgr.cfgs[cfgID]["FLD_TYPE"]
                cfgDict["name"] = utlp.incrementMatching(str(name), 
                                                         allNames,  
                                                         maxLength=15)
                allNames.add(cfgDict["name"])

                didWork = utlp.cfgChange(pmgr, cfgID, cfgDict)
                
                if verbose: 
	                if didWork: print "        Completed update"
	                else: print "        Failed to update the cfg with new values"
		
            continue
        

        try:
            # Create a unique name for the config and then add the new config
            cfgDict["name"] = utlp.nextCfgName(pmgr, name)
            CfgID = utlp.newConfig(pmgr, cfgDict, cfgDict["name"])

            pmgr.updateTables()

            # Create a unique name for the obj and then add it
            objDict["name"] = utlp.nextObjName(pmgr, name)
            ObjID = utlp.newObject(pmgr, objDict)
        
            pmgr.updateTables()
            
            # Set the obj to use the cfg settings
            status = False            
            status = utlp.setObjCfg(pmgr, ObjID, CfgID)
            
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
	try: utlp.printDiff(pmgr, objLive, cfgLive, objPmgr, cfgPmgr, verbose) 
	except: pass


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


###############################################################################
## 					   	 		     Main									 ## 
###############################################################################


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
	else: hutchpath = []


	# Try import first
	if arguments["import"]:
		hutches, objType = utlp.motorPrelimChecks(hutchPaths, hutches, None, verbose)[0:1]
		hutchPaths = utlp.motorPrelimChecks(hutchPaths, hutchPaths, None, verbose)[0]
		
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
		print "Motor PV: {0}".format(PV)
		m_DESC = caget(PV + ".DESC")
		print "Motor description: {0}".format(m_DESC)
		if not SNs[PV]: continue
		else: SN = SNs[PV]
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
				dumbMotorApply(PV, hutch, objType, SN, verbose, zenity)
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
