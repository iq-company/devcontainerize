#!/usr/bin/bash

set -e

# Those patches are separated from docker-patches, as they can also be applied in a local setup without docker:
# (They may not address files/directories from absolute docker paths but always relative from within the bench directory)
#
# This script is called with user *iqa* in directory /home/iqa/ or from within a bench directory.
# The calling cwd decides where the frappe source code relies:
# either in	/tmp/bench/apps/frappe
# or cwd/apps/frappe
# (call it locally with: `bash apps/iq_core/delivery/resources/frappe-patches.sh`)

CWD="$(pwd)"

if [ "$CWD" = "/home/iqa" ]; then
	FRAPPE_TARGET_DIR="/tmp/bench/apps/frappe"
elif [ -d "apps" ] && [ -d "sites" ]; then
	FRAPPE_TARGET_DIR="${CWD}/apps/frappe"
else
	# Case 3: Invalid CWD, exit with error
	echo "Error: Invalid current working directory."
	exit 1
fi

echo "APP_TARGET_DIR=$FRAPPE_TARGET_DIR"

# remove unneeded frappe libs
unneeded_libs=(
	"PyMySQL"
	"PyQRCode"
	"ldap3"
	"terminaltables"
	"dropbox"
	"google-api-python-client"
	"google-auth-oauthlib"
	"google-auth"
	"posthog"
	"maxminddb-geolite2"
	"sentry-sdk"
	"vobject"
	"weasyprint"
	"pypdf" # remove pypdf from frappe pyproject.toml, but keep it in iq_core in a newer version
)

for lib in "${unneeded_libs[@]}"; do
	sed -Ei "/$lib[[:space:]]*[~>=\!]+/d" $FRAPPE_TARGET_DIR/pyproject.toml
done

# patch removed dependencies
# removes multiline ldap3 imports
sed -i '/^import ldap3/d; /^from ldap3[^(]*$/d; /^from ldap3[^(]*(/,/^[[:space:]]*)/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/ldap_settings/ldap_settings.py
sed -i 's/ldap3\.Connection:/"ldap3.Connection":/' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/ldap_settings/ldap_settings.py
sed -i 's/: ldap3\.Connection/: "ldap3.Connection"/' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/ldap_settings/ldap_settings.py
sed -i 's/: Entry/: "Entry"/' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/ldap_settings/ldap_settings.py
# removes single lines of unneeded (and removed) imports to prevent loading issues (but files aren't usable anymore)
sed -i '/import dropbox/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/dropbox_settings/dropbox_settings.py
sed -i '/import posthog/d' $FRAPPE_TARGET_DIR/frappe/utils/telemetry.py
sed -i '/from posthog/d' $FRAPPE_TARGET_DIR/frappe/utils/telemetry.py
sed -i '/from google/d' $FRAPPE_TARGET_DIR/frappe/integrations/google_oauth.py
sed -i '/import google/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_calendar/google_calendar.py
sed -i '/from google/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_calendar/google_calendar.py
sed -i '/from frappe.integrations.google/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_calendar/google_calendar.py
sed -i '/from google/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_contacts/google_contacts.py
sed -i '/from frappe.integrations.google/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_contacts/google_contacts.py
sed -i '/from google/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_drive/google_drive.py
sed -i '/from googleapiclient/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_drive/google_drive.py
sed -i '/from apiclient/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_drive/google_drive.py
sed -i '/from frappe.integrations.google/d' $FRAPPE_TARGET_DIR/frappe/integrations/doctype/google_drive/google_drive.py
sed -i '/from google/d' $FRAPPE_TARGET_DIR/frappe/website/doctype/website_settings/google_indexing.py
sed -i '/from frappe.integrations.google/d' $FRAPPE_TARGET_DIR/frappe/website/doctype/website_settings/google_indexing.py

# sentry
sed -i '/from frappe.utils.sentry/d' $FRAPPE_TARGET_DIR/frappe/utils/error.py
sed -i '/capture_exception/d' $FRAPPE_TARGET_DIR/frappe/utils/error.py

# db patches
sed -i "/import frappe.database.mariadb.database/d" $FRAPPE_TARGET_DIR/frappe/app.py

sed -i '/frappe\.database\.mariadb\.database/d' $FRAPPE_TARGET_DIR/frappe/__init__.py
sed -i 's/^\([[:space:]]*\)db: MariaDBDatabase | PostgresDatabase$/\1db: PostgresDatabase/' $FRAPPE_TARGET_DIR/frappe/__init__.py
sed -i 's/^\([[:space:]]*\)qb: MariaDB | Postgres$/\1qb: Postgres/' $FRAPPE_TARGET_DIR/frappe/__init__.py
sed -i 's/MariaDBDatabase\.default_port/"3306"/g' $FRAPPE_TARGET_DIR/frappe/__init__.py

pg_db_file="$FRAPPE_TARGET_DIR/frappe/database/postgres/database.py"

# Check if def connect(self) is already present in the file (then the new version was applied)
if grep -q "def connect(self)" "$pg_db_file"; then
	echo "Method 'def connect(self)' already exists, no changes made."

	if $CWD == "/home/iqa"; then
		echo "It seems postgres' connect(self) method was patched in base branch. Need to verify that the following patches are applied:"
		exit 1
	fi
else
	echo "Method 'def connect(self)' missing, patching database/database.py ..."

	#
	# Insert code before "def get_connection(self):" definition: ######
	#
	# Inject connect with schema setting
	awk '/^[[:space:]]*def get_connection\(self\):/ {print "	def connect(self):\n		super().connect()\n\n		self._cursor.execute(\"SET search_path TO %s\", (frappe.conf.get(\"db_schema\", \"public\"),))\n"; print} !/^[[:space:]]*def get_connection\(self\):/ {print}' "$pg_db_file" >temp_file && mv temp_file "$pg_db_file"

	# Inject begin with schema setting
	# TODO: Create PR for this part. On frappe.db.rollback() the schema search_path is not set anymore:
	# Refer: apps/frappe/frappe/sessions.py:
	#		in def update() run call fails if rollback is called in apps/frappe/frappe/app.py #sync_database()
	#		(common case after a bit inactivity and call in PORTAL VIEW on: http://host.local/)
	#
	awk '/^[[:space:]]*def get_connection\(self\):/ {print "	def begin(self, *, read_only=False):\n		super().begin(read_only=read_only)\n\n		self._cursor.execute(\"SET search_path TO %s\", (frappe.conf.get(\"db_schema\", \"public\"),))\n"; print} !/^[[:space:]]*def get_connection\(self\):/ {print}' "$pg_db_file" >temp_file && mv temp_file "$pg_db_file"

	# remove pymysql imports
	sed -i '/^[[:space:]]*\(from pymysql\|import pymysql\)/d' $FRAPPE_TARGET_DIR/frappe/database/database.py
	sed -i -E 's/"Mariadb(Connection|Cursor)" \| //g' $FRAPPE_TARGET_DIR/frappe/database/database.py

	# add a rollback to sql command exception for postgres (if it seems to be a reliable solution include it to PR)
	awk '/^[[:space:]]*if self\.is_syntax_error\(e\):/ {print "			if self.db_type == \"postgres\":\n				self.rollback()\n"; print} !/^[[:space:]]*if self\.is_syntax_error\(e\):/ {print}' "$FRAPPE_TARGET_DIR/frappe/database/database.py" >temp_file && mv temp_file "$FRAPPE_TARGET_DIR/frappe/database/database.py"

	# hide tmp postgres error output
	sed -i 's/elif self\.db_type == "postgres":/elif self.db_type == "postgres-skip-error-output":/g' "$FRAPPE_TARGET_DIR/frappe/database/database.py"

	echo "Code patched successfully."
fi

# frappe js lib patches #######################################
# remove dependency from package.json - newer version is included in vue package
sed -i '/@vue\/component-compiler/d' $FRAPPE_TARGET_DIR/package.json
# The following patch leads to errors with websocket and was not necessary the last time.
# sed -i 's/"@editorjs\/editorjs": "~2.26.3"/"@editorjs\/editorjs": "^2.29.1"/' $FRAPPE_TARGET_DIR/package.json

# ignored frappe billing app
jq 'del(.scripts.postinstall)' $FRAPPE_TARGET_DIR/package.json >$FRAPPE_TARGET_DIR/package.tmp.json && mv $FRAPPE_TARGET_DIR/package.tmp.json $FRAPPE_TARGET_DIR/package.json

# Actually this package is only used after sass/assets are built, so it is removed after that totally to also reduce img size
# # Update fast-glob because of micromatch dependency and CVE
# sed -i '/"fast-glob":/ s/\^3\.[0-9.]\+/\^3.3.2/' $FRAPPE_TARGET_DIR/package.json

# patch/enforce @adobe/css-tools@~4.3.3 version (from 4.3.1)
jq '.resolutions = (.resolutions // {}) + {"@adobe/css-tools": "4.3.3"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"

# patch/enforce loadjs@4.3.0 version
jq '.resolutions = (.resolutions // {}) + {"loadjs": "4.3.0"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"

# patch/enforce loader-utils@1.4.2 version
jq '.resolutions = (.resolutions // {}) + {"loader-utils": "^3.2.0"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"

# patch/enforce clean-css@5.2.2 version
jq '.resolutions = (.resolutions // {}) + {"@vue/component-compiler/clean-css": "5.2.2"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"

jq '.resolutions = (.resolutions // {}) + {"postcss-modules-sync/generic-names": "4.0.0"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"
jq '.resolutions = (.resolutions // {}) + {"postcss": "8.4.47"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"
jq '.resolutions = (.resolutions // {}) + {"braces": "3.0.3"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"
jq '.resolutions = (.resolutions // {}) + {"ws": "8.18.0"}' "$FRAPPE_TARGET_DIR/package.json" >tmp.$$.json && mv tmp.$$.json "$FRAPPE_TARGET_DIR/package.json"

# update jquery
rm -f $FRAPPE_TARGET_DIR/frappe/public/js/lib/jquery/jquery.min.js
wget -O $FRAPPE_TARGET_DIR/frappe/public/js/lib/jquery/jquery.min.js https://code.jquery.com/jquery-3.7.1.min.js
