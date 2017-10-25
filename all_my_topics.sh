#!/bin/bash

declare -a AllProfiles
declare -a ProfileBuckets

#AllProfiles=(default Primary Secondary Nasdaq-Prod Nasdaq-Dev Nasdaq-DR)
AllProfiles=( $(./Allprofiles.sh programmatic | awk '(NR>5 && $1 !~ /^-/) {print $1}') )

NumofProfiles=${#AllProfiles[@]}
echo "Found ${NumofProfiles} profiles in credentials file"
echo "Outputting all SNS topics from all profiles"

printf "%-20s %-50s \n" "Profile" "Topic Name"
printf "%-20s %-50s \n" "-------" "-----------"
for profile in ${AllProfiles[@]}; do
	aws sns list-topics --output text --query 'Topics[].TopicArn' --profile $profile | awk -F $"\t" -v var=${profile} '{for (i=1;i<=NF;i++) printf "%-20s %-50s \n",var,$i}' 
	echo "----------------"
done

echo
exit 0
