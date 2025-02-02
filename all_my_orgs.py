#!/usr/bin/env python3

"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import sys
import logging
import argparse
import Inventory_Modules

from botocore.exceptions import ClientError, NoCredentialsError, InvalidConfigError
from colorama import init,Fore,Style

init()

parser = argparse.ArgumentParser(
	description="We\'re going to find all accounts within any of the organizations we have access to.",
	prefix_chars='-+/')
ProfileGroup = parser.add_mutually_exclusive_group()
ProfileGroup.add_argument(
	"-p","--profile",
	dest="pProfile",
	metavar="Profile",
	default="all",	# Default to everything
	help="Which single profile do you want to run for?")
ProfileGroup.add_argument(
	"-l","--listprofiles",
	dest="pProfiles",
	metavar="Profiles",
	nargs="*",
	default=[],	# Default to nothing
	help="Which list of profiles do you want to run for?")
parser.add_argument(
	'-R', '--root',
	help="Display only the root accounts found in the profiles",
	action="store_const",
	dest="rootonly",
	const=True,
	default=False)
parser.add_argument(
	'-s', '--q', '--short',
	help="Display only brief listing of the root accounts, and not the Child Accounts under them",
	action="store_const",
	dest="shortform",
	const=True,
	default=False)
parser.add_argument(
	'-v',
	help="Be verbose",
	action="store_const",
	dest="loglevel",
	const=logging.ERROR, # args.loglevel = 40
	default=logging.CRITICAL) # args.loglevel = 50
parser.add_argument(
	'-vv', '--verbose',
	help="Be MORE verbose",
	action="store_const",
	dest="loglevel",
	const=logging.WARNING, # args.loglevel = 30
	default=logging.CRITICAL) # args.loglevel = 50
parser.add_argument(
	'-vvv',
	help="Print debugging statements",
	action="store_const",
	dest="loglevel",
	const=logging.INFO,	# args.loglevel = 20
	default=logging.CRITICAL) # args.loglevel = 50
parser.add_argument(
	'-d', '--debug',
	help="Print LOTS of debugging statements",
	action="store_const",
	dest="loglevel",
	const=logging.DEBUG,	# args.loglevel = 10
	default=logging.CRITICAL) # args.loglevel = 50
args=parser.parse_args()

pProfile=args.pProfile
pProfiles=args.pProfiles
verbose=args.loglevel
rootonly=args.rootonly
shortform=args.shortform
logging.basicConfig(level=args.loglevel, format="[%(filename)s:%(lineno)s:%(levelname)s - %(funcName)20s() ] %(message)s")

SkipProfiles=["default"]
ERASE_LINE = '\x1b[2K'

RootAccts=[]	# List of the Organization Root's Account Number
RootProfiles=[]	# List of the Organization Root's profiles

"""
Because there's two ways for the user to provide profiles, we have to consider four scenarios:
	1. They provided no input
		* We'll use the pProfile default of "all"
	2. They provided input using the pProfile parameter of a specific profile
		* That's the case we already handle
	3. They provided a list of profiles using the pProfiles parameter
		* This is the new case, that we'll cycle through
	4. They provided both the pProfile AND pProfiles parameters.
		* argparse will stop the user from doing that!

"""

logging.info("Profile: %s",pProfile)
logging.info("Profiles: %s",str(pProfiles))

if pProfile == "all" and pProfiles == []: # Use case #1 from above
	logging.info("Use Case #1")
	logging.warning("Profile is set to all")
	ShowEverything=True
elif not pProfile == "all":	# Use case #2 from above
	logging.info("Use Case #2")
	logging.warning("Profile is set to %s",pProfile)
	AcctNum = Inventory_Modules.find_account_number(pProfile)
	AcctAttr = Inventory_Modules.find_org_attr(pProfile)
	MasterAcct = AcctAttr['MasterAccountId']
	OrgId = AcctAttr['Id']
	if AcctNum==MasterAcct:
		logging.warning("This is a root account - showing info only for %s",pProfile)
		RootAcct=True
		ShowEverything=False
	else:
		print()
		print(Fore.RED + "If you're going to provide a profile, it's supposed to be a Master Billing Account profile!!" + Fore.RESET)
		print("Continuing to run the script - but for all profiles.")
		ShowEverything=True
else: # Use case #3 from above
	logging.info("Use Case #3")
	logging.warning("Multiple profiles have been provided: %s. Going through one at a time...",str(pProfiles))
	for profile in pProfiles:
		AcctNum = Inventory_Modules.find_account_number(profile)
		AcctAttr = Inventory_Modules.find_org_attr(profile)
		MasterAcct = AcctAttr['MasterAccountId']
		OrgId = AcctAttr['Id']
		if AcctNum==MasterAcct:
			filename=sys.argv[0]
			logging.info("Running the script again with %s as your profile",profile)
			ShowEverything=False
			os.system("python3 "+filename+" -p "+profile)
		else:
			print()
			print(Fore.RED + "Provided profile: {} isn't a Master Billing Account profile!!".format(profile) + Fore.RESET)
			print("Skipping...")
			ShowEverything=False
			continue
	sys.exit("Finished %s profiles!" % len(pProfiles))	# Finished the multiple profiles provided.

"""
TODO:
	- If they provide a profile that isn't a root profile, you should find out which org it belongs to, and then show the org for that. This will be difficult, since we don't know which profile that belongs to. Hmmm...
"""

if ShowEverything:
	fmt='%-23s %-15s %-27s %-12s %-10s'
	print ("------------------------------------")
	print (fmt % ("Profile Name","Account Number","Master Org Acct","Org ID","Root Acct?"))
	print (fmt % ("------------","--------------","---------------","------","----------"))
	for profile in Inventory_Modules.get_profiles2(SkipProfiles,"all"):
		AcctNum = "Blank Acct"
		MasterAcct = "Blank Root"
		OrgId = "o-xxxxxxxxxx"
		Email = "Email not available"
		RootId = "r-xxxx"
		ErrorFlag = False
		try:
			AcctNum = Inventory_Modules.find_account_number(profile)
			logging.info("AccountNumber: {}".format(AcctNum))
			if AcctNum == '123456789012':
				ErrorFlag = True
				pass
			else:
				AcctAttr = Inventory_Modules.find_org_attr(profile)
				MasterAcct = AcctAttr['MasterAccountId']
				OrgId = AcctAttr['Id']
		except ClientError as my_Error:
			ErrorFlag = True
			if str(my_Error).find("AWSOrganizationsNotInUseException") > 0:
				MasterAcct="Not an Org Account"
			elif str(my_Error).find("AccessDenied") > 0:
				MasterAcct="Acct not auth for Org API."
			elif str(my_Error).find("InvalidClientTokenId") > 0:
				MasterAcct="Credentials Invalid."
			elif str(my_Error).find("ExpiredToken") > 0:
				MasterAcct="Token Expired."
			else:
				print("Client Error")
				print(my_Error)
		except InvalidConfigError as my_Error:
			ErrorFlag = True
			if str(my_Error).find("does not exist") > 0:
				ErrorMessage=str(my_Error)[str(my_Error).find(":"):]
				print(ErrorMessage)
			else:
				print("Credentials Error")
				print(my_Error)

		except NoCredentialsError as my_Error:
			ErrorFlag = True
			if str(my_Error).find("Unable to locate credentials") > 0:
				MasterAcct="This profile doesn't have credentials."
			else:
				print("Credentials Error")
				print(my_Error)
		if AcctNum==MasterAcct and not ErrorFlag:
			RootAcct=True
			RootAccts.append(MasterAcct)
			RootProfiles.append(profile)
			Email = AcctAttr['MasterAccountEmail']
			logging.info('Email: %s',Email)
		else:
			RootAcct=False

		'''
		If I create a dictionary from the Root Accts and Root Profiles Lists - 
		I can use that to determine which profile belongs to the root user of my (child) account.
		But this dictionary is only guaranteed to be valid after ALL profiles have been checked, 
		so... it doesn't solve our issue - unless we don't write anything to the screen until *everything* is done, 
		and we keep all output in another dictionary - where we can populate the missing data at the end... 
		but that takes a long time, since nothing would be sent to the screen in the meantime.
		'''
		# dictionary.update(dict(zip(RootAccts, RootProfiles)))

	#	 Print results for this profile
		if RootAcct:
			print(Fore.RED + fmt % (profile,AcctNum,MasterAcct,OrgId,RootAcct)+Style.RESET_ALL)
		elif rootonly: # If I'm looking for only the root accounts, when I find something that isn't a root account, don't print anything and continue on.
			print(ERASE_LINE,"{} isn't a root account".format(profile),end="\r")
		else:
			print (fmt % (profile,AcctNum,MasterAcct,OrgId,RootAcct))
	print()
	print("-------------------")

	if not shortform:
		fmt='%-23s %-15s %-6s'
		child_fmt="\t\t%-20s %-20s"
		print()
		print(fmt % ("Organization's Profile","Root Account","ALZ"))
		print(fmt % ("----------------------","------------","---"))
		NumOfAccounts=0
		for profile in RootProfiles:
			child_accounts={}
			MasterAcct=Inventory_Modules.find_account_number(profile)
			child_accounts=Inventory_Modules.find_child_accounts(profile)
			landing_zone=Inventory_Modules.find_if_alz(profile)['ALZ']
			NumOfAccounts=NumOfAccounts + len(child_accounts)
			if landing_zone:
				fmt='%-23s '+Style.BRIGHT+'%-15s '+Style.RESET_ALL+Fore.RED+'%-6s '+Fore.RESET
			else:
				fmt='%-23s '+Style.BRIGHT+'%-15s '+Style.RESET_ALL+'%-6s'
			print(fmt % (profile,MasterAcct,landing_zone))
			print(child_fmt % ("Child Account Number","Child Email Address"))
			for account in sorted(child_accounts):
				print(child_fmt % (account,child_accounts[account]))
		print()
		print("Number of Organizations:",len(RootProfiles))
		print("Number of Organization Accounts:",NumOfAccounts)
elif not ShowEverything:
	fmt='%-23s %-15s %-6s'
	child_fmt="\t\t%-20s %-20s"
	print()
	print(fmt % ("Organization's Profile","Root Account","ALZ"))
	print(fmt % ("----------------------","------------","---"))
	NumOfAccounts=0

	child_accounts={}
	MasterAcct=Inventory_Modules.find_account_number(pProfile)
	child_accounts=Inventory_Modules.find_child_accounts(pProfile)
	landing_zone=Inventory_Modules.find_if_alz(pProfile)['ALZ']
	NumOfAccounts=NumOfAccounts + len(child_accounts)
	if landing_zone:
		fmt='%-23s '+Style.BRIGHT+'%-15s '+Style.RESET_ALL+Fore.RED+'%-6s '+Fore.RESET
	else:
		fmt='%-23s '+Style.BRIGHT+'%-15s '+Style.RESET_ALL+'%-6s'
	print(fmt % (pProfile,MasterAcct,landing_zone))
	print(child_fmt % ("Child Account Number","Child Email Address"))
	for account in sorted(child_accounts):
		print(child_fmt % (account,child_accounts[account]))
	print()
	print("Number of Organization Accounts:",NumOfAccounts)
