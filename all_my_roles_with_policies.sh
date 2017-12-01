#!/bin/bash

declare -a AllProfiles
declare -a AcctRoles

echo "Gathering your profiles..."
AllProfiles=( $(./Allprofiles.sh programmatic | awk '(NR>5 && $1 !~ /^-/) {print $1}') )

NumofProfiles=${#AllProfiles[@]}
echo "Found ${NumofProfiles} profiles in credentials file"
echo "Outputting all Roles from all profiles"

format='%-15s %-65s %-18s %-60s \n'

printf "$format" "Profile" "Role Name" "Policy Type" "AttachedPolicies"
printf "$format" "-------" "---------" "-----------" "----------------"
# Cycles through each profile
for profile in ${AllProfiles[@]}; do
	# Cycles through each role within the profile
	AcctRoles=( $(aws iam list-roles --output text --query 'Roles[].RoleName' --profile $profile | tr '\t' '\n'))
	for role in ${AcctRoles[@]}; do
		# This will output each policy associated with the specific role
		aws iam list-attached-role-policies --role-name $role --profile $profile --output text --query 'AttachedPolicies[].PolicyName' | tr '\t' '\n' | awk -F $"\t" -v var=${profile} -v var2=${role} -v fmt="${format}" '{printf fmt,var,var2,"AWS Managed",$1}'
		aws iam list-role-policies --role-name $role --profile $profile --output text --query 'PolicyNames' | tr '\t' '\n' | awk -F $"\t" -v var=${profile} -v var2=${role} -v fmt="${format}" '{printf fmt,var,var2,"In-line Policies",$1}'
	done
	echo "----------------"

done

echo
exit 0
