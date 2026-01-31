#!/bin/bash

rm -f /tmp/appName.txt

read -p "Enter the app name (lower case, no spaces, no special characters): " appName

# strip and trim the input
appName=$(echo $appName | tr -d '[:space:]' | tr -d '[:punct:]' | tr '[:upper:]' '[:lower:]')
echo $appName > /tmp/appName.txt

# check if appName was empty; if so skip
if [ -z "$appName" ]; then
	echo "App name was empty; skipping..."
	exit 1
fi

