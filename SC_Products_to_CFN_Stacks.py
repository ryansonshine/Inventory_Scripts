#!/usr/local/bin/python3

import os, sys, pprint, boto3
import Inventory_Modules
import argparse
from colorama import init,Fore,Back,Style
from botocore.exceptions import ClientError, NoCredentialsError

import logging

init()

# UsageMsg="You can provide a level to determine whether this script considers only the 'credentials' file, the 'config' file, or both."
parser = argparse.ArgumentParser(
	description="We\'re going to find all resources within any of the profiles we have access to.",
	prefix_chars='-+/')
parser.add_argument(
	"-p","--profile",
	dest="pProfile",
	metavar="profile to use",
	default="default",
	help="To specify a specific profile, use this parameter. Default will be your default profile.")
parser.add_argument(
	"-f","--fragment",
	dest="pstackfrag",
	metavar="CloudFormation stack fragment",
	default="all",
	help="String fragment of the cloudformation stack or stackset(s) you want to check for.")
parser.add_argument(
	"-s","--status",
	dest="pstatus",
	metavar="CloudFormation status",
	default="active",
	help="String that determines whether we only see 'CREATE_COMPLETE' or 'DELETE_COMPLETE' too")
parser.add_argument(
	"-r","--region",
	dest="pregion",
	metavar="region name string",
	default="us-east-1",
	help="String fragment of the region(s) you want to check for resources.")
parser.add_argument(
	"+delete","+forreal",
	dest="DeletionRun",
	const=True,
	default=False,
	action="store_const",
	help="This will delete the stacks found - without any opportunity to confirm. Be careful!!")
parser.add_argument(
    '-d', '--debug',
    help="Print lots of debugging statements",
    action="store_const",
	dest="loglevel",
	const=logging.INFO,	# args.loglevel = 20
    default=logging.CRITICAL) # args.loglevel = 50
parser.add_argument(
    '-v', '--verbose',
    help="Be verbose",
    action="store_const",
	dest="loglevel",
	const=logging.ERROR) # args.loglevel = 40
parser.add_argument(
    '-vv',
    help="Be MORE verbose",
    action="store_const",
	dest="loglevel",
	const=logging.WARNING) # args.loglevel = 30
args = parser.parse_args()

pProfile=args.pProfile
pRegion=args.pregion
pstackfrag=args.pstackfrag
pstatus=args.pstatus
verbose=args.loglevel
DeletionRun=args.DeletionRun
logging.basicConfig(level=args.loglevel, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')

##########################
def sort_by_email(elem):
	return(elem('AccountEmail'))
##########################
ERASE_LINE = '\x1b[2K'

print()
fmt='%-15s %-42s %-35s %-10s %-18s %-20s'
print(fmt % ("Account Number","SC Product Name","CFN Stack Name","SC Status","CFN Stack Status","AccountEmail"))
print(fmt % ("--------------","---------------","--------------","---------","----------------","------------"))

SCP2Stacks=[]
SCProducts=[]
session_cfn=boto3.Session(profile_name=pProfile,region_name=pRegion)
client_cfn=session_cfn.client('cloudformation')
try:
	# SCProducts=Inventory_Modules.find_sc_products(pProfile,pRegion,"ERROR")
	SCresponse=Inventory_Modules.find_sc_products(pProfile,pRegion,"All")
	logging.warning("A list of the SC Products found:")
	for i in range(len(SCresponse['ProvisionedProducts'])):
		logging.warning("SC Product Name %s | SC Product Status %s", SCresponse['ProvisionedProducts'][i]['Name'], SCresponse['ProvisionedProducts'][i]['Status'])
		SCProducts.append({
			'SCPName':SCresponse['ProvisionedProducts'][i]['Name'],
			'SCPId':SCresponse['ProvisionedProducts'][i]['Id'],
			'SCPStatus':SCresponse['ProvisionedProducts'][i]['Status']
		})
	for i in range(len(SCProducts)):
		print(ERASE_LINE,Fore.RED+"Checking",i,"of",len(SCProducts),"products "+Fore.RESET,end='\r')
		CFNresponse=Inventory_Modules.find_stacks(pProfile,pRegion,SCProducts[i]['SCPId'],"all")
		logging.error("Length of response is %s for SC Name %s", len(CFNresponse),SCProducts[i]['SCPName'])
		if len(CFNresponse) > 0:
			stack_info=client_cfn.describe_stacks(
				 StackName=CFNresponse[0]['StackName']
			)
			if len(stack_info['Stacks'][0]['Parameters']) > 0:
				for y in range(len(stack_info['Stacks'][0]['Parameters'])):
					if stack_info['Stacks'][0]['Parameters'][y]['ParameterKey']=='AccountEmail':
						AccountEmail=stack_info['Stacks'][0]['Parameters'][y]['ParameterValue']
			else:
				AccountEmail='None'
			if 'Outputs' in stack_info['Stacks'][0].keys():
				AccountID='None'
				for y in range(len(stack_info['Stacks'][0]['Outputs'])):
					logging.error("Output Key %s for stack %s is %s", stack_info['Stacks'][0]['Outputs'][y]['OutputKey'], CFNresponse[0]['StackName'], stack_info['Stacks'][0]['Outputs'][y]['OutputValue'])
					if stack_info['Stacks'][0]['Outputs'][y]['OutputKey']=='AccountID':
						AccountID=stack_info['Stacks'][0]['Outputs'][y]['OutputValue']
					else:
						logging.info("Outputs key present, but no account ID")
			else:
				logging.info("No Outputs key present")
				AccountID='None'
			SCP2Stacks.append({
				'SCProductName':SCProducts[i]['SCPName'],
				'SCProductId':SCProducts[i]['SCPId'],
				'SCStatus':SCProducts[i]['SCPStatus'],
				'CFNStackName':CFNresponse[0]['StackName'],
				'CFNStackStatus':CFNresponse[0]['StackStatus'],
				'AccountEmail':AccountEmail,
				'AccountID':AccountID
			})
	# sorted_list=sorted(SCP2Stacks, key=sort_by_email)
	# SCP2Stacks=sorted_list
	for i in range(len(SCP2Stacks)):
		if SCP2Stacks[i]['SCStatus']=='ERROR':
			print(Fore.RED + fmt % (SCP2Stacks[i]['AccountID'], SCP2Stacks[i]['SCProductName'], SCP2Stacks[i]['CFNStackName'], SCP2Stacks[i]['SCStatus'], SCP2Stacks[i]['CFNStackStatus'],  SCP2Stacks[i]['AccountEmail'])+Style.RESET_ALL)
		else:
			print(fmt % (SCP2Stacks[i]['AccountID'], SCP2Stacks[i]['SCProductName'], SCP2Stacks[i]['CFNStackName'], SCP2Stacks[i]['SCStatus'], SCP2Stacks[i]['CFNStackStatus'],  SCP2Stacks[i]['AccountEmail']))
except ClientError as my_Error:
	if str(my_Error).find("AuthFailure") > 0:
		print(pProfile+": Authorization Failure ")
	elif str(my_Error).find("AccessDenied") > 0:
		print(pProfile+": Access Denied Failure ")
	else:
		print(pProfile+": Other kind of failure ")
		print (my_Error)

print()
# print("You probably want to remove the following SC Products:")
# StacksAndProductsToDelete=[]
# for i in range(len(SCP2Stacks)):

# for i in range(len(SCP2Stacks)):
# 	if SCP2Stacks[i]['SCStatus']=='ERROR':
# 		print("aws servicecatalog terminate-provisioned-product --provisioned-product-id",SCP2Stacks[i]['SCProductId'])
"""
if DeletionRun:
	logging.warning("Deleting %s stacks",len(StacksFound))
	for y in range(len(StacksFound)):
		role_arn = "arn:aws:iam::{}:role/AWSCloudFormationStackSetExecutionRole".format(StacksFound[y]['Account'])
		cfn_client=aws_session.client('cloudformation')
		account_credentials = sts_client.assume_role(
			RoleArn=role_arn,
			RoleSessionName="Find-Stacks")['Credentials']
		account_credentials['AccountNumber']=StacksFound[y]['Account']
		print("Deleting stack {} from Account {} in region {} with status: {}".format(StacksFound[y]['StackName'],StacksFound[y]['Account'],StacksFound[y]['Region'],StacksFound[y]['StackStatus']))
		# This next line is BAD because it's hard-coded for GuardDuty, but we'll fix that eventually
		if StacksFound[y]['StackStatus'] == 'DELETE_FAILED':
			# This deletion generally fails because the Master Detector doesn't properly delete (and it's usually already deleted due to some other script) - so we just need to delete the stack anyway - and ignore the actual resource.
			response=Inventory_Modules.delete_stack2(account_credentials,StacksFound[y]['Region'],StacksFound[y]['StackName'],RetainResources=True,ResourcesToRetain=["MasterDetector"])
		else:
			response=Inventory_Modules.delete_stack2(account_credentials,StacksFound[y]['Region'],StacksFound[y]['StackName'])
elif DeletionRun:
	logging.warning("Deleting %s stacks",len(StacksFound))
	for y in range(len(StacksFound)):
		print("Deleting stack {} from account {} in region {} with status: {}".format(StacksFound[y]['StackName'],StacksFound[y]['Account'],StacksFound[y]['Region'],StacksFound[y]['StackStatus']))
		response=Inventory_Modules.delete_stack2(account_credentials,StacksFound[y]['Region'],StacksFound[y]['StackName'])

"""

print()
print("Thanks for using this script...")
