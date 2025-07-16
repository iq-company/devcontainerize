# PowerShell script to create a single .env file if it doesn't exist
# This script is called by VSCode devcontainer initializeCommand

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Determine .devcontainer directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$opsDir = Join-Path $scriptDir ".."

$targetEnvFile = Join-Path $opsDir "compose/.env"
$templateFile = Join-Path $opsDir "env/.env.template"

# --- Handle DBMS selection (always run) ---

# Determine DBMS choice (argument, then environment variable, then default)
$dbms = ""
if ($args.Count -gt 0) {
    $dbms = $args[0].ToLower()
} elseif ($env:DEVCONTAINER_DBMS) {
    $dbms = $env:DEVCONTAINER_DBMS.ToLower()
} else {
    $dbms = "postgres"
}

if ($dbms -ne "postgres" -and $dbms -ne "mariadb") {
    Write-Host "Warning: Invalid DBMS specified ($dbms). Defaulting to postgres."
    $dbms = "postgres"
}

$dbHostVal = ""
$dbPortVal = ""
if ($dbms -eq "postgres") {
    $dbHostVal = "pg"
    $dbPortVal = "5432"
} elseif ($dbms -eq "mariadb") {
    $dbHostVal = "mariadb"
    $dbPortVal = "3306"
}

# --- Create .env file if it doesn't exist ---

if (Test-Path $targetEnvFile) {
    Write-Host "Environment file '$targetEnvFile' already exists. Skipping creation."
} else {
    Write-Host "Creating environment file '$targetEnvFile'..."

    # --- Gather required values ---

    # Get current UID and GID (for Linux/WSL compatibility)
    # In a devcontainer, these should typically be available.
    # Fallback to 1000 if not found, though this might not be ideal for all scenarios.
    try {
        $currentUid = (id -u).Trim()
        $currentGid = (id -g).Trim()
    } catch {
        Write-Warning "Could not determine UID/GID. Defaulting to 1000."
        $currentUid = "1000"
        $currentGid = "1000"
    }

    # Generate 5 random lowercase letters
    $charsLower = 'abcdefghijklmnopqrstuvwxyz'
    $randomLower = -join (1..5 | ForEach-Object { $charsLower[(Get-Random -Maximum $charsLower.Length)] })

    # Determine VSCode settings path
    if (Test-Path "$env:APPDATA\Code\User") { # Windows
        $vscodeSettingsPath = "$env:APPDATA\Code\User\"
    } elseif (Test-Path "$env:HOME/.config/Code/User") { # Linux
        $vscodeSettingsPath = "$env:HOME/.config/Code/User/"
    } else {
        $vscodeSettingsPath = "/tmp/.vscode-host"
    }

    # --- Generate random passwords and user names ---
    $charsAlphanumeric = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    $iqAdminPwVal = -join (1..16 | ForEach-Object { $charsAlphanumeric[(Get-Random -Maximum $charsAlphanumeric.Length)] })
    $dbSuperUserVal = "ddl_user_" + (-join (1..5 | ForEach-Object { $charsAlphanumeric[(Get-Random -Maximum $charsAlphanumeric.Length)] }))
    $dbSuperUserPwVal = -join (1..16 | ForEach-Object { $charsAlphanumeric[(Get-Random -Maximum $charsAlphanumeric.Length)] })
    $dbRootPasswordVal = -join (1..16 | ForEach-Object { $charsAlphanumeric[(Get-Random -Maximum $charsAlphanumeric.Length)] })
    $dbPasswordVal = -join (1..16 | ForEach-Object { $charsAlphanumeric[(Get-Random -Maximum $charsAlphanumeric.Length)] })

    # --- Create file from template and replace placeholders ---

    Copy-Item $templateFile -Destination $targetEnvFile

    $content = Get-Content $targetEnvFile -Raw

    # General placeholders
    $content = $content -replace '{{random_lower}}', $randomLower
    $content = $content -replace '{{vscode_settings_path}}', $vscodeSettingsPath
    $content = $content -replace '{{uid}}', $currentUid
    $content = $content -replace '{{gid}}', $currentGid
    $content = $content -replace 'IQ_ADMIN_PW={{random_password}}', "IQ_ADMIN_PW=$iqAdminPwVal"

    # Database placeholders
    $content = $content -replace '{{db_host}}', $dbHostVal
    $content = $content -replace '{{db_port}}', $dbPortVal
    $content = $content -replace '{{db_super_user}}', $dbSuperUserVal
    $content = $content -replace '{{db_super_user_pw}}', $dbSuperUserPwVal
    $content = $content -replace '{{db_root_password}}', $dbRootPasswordVal
    $content = $content -replace '{{db_password}}', $dbPasswordVal
    $content = $content -replace '{{dbms}}', $dbms

    $content | Set-Content $targetEnvFile

    # --- Append DBMS-specific addon if it exists ---
    $addonFile = Join-Path $opsDir "env/.env.$dbms.addon.template"
    if (Test-Path $addonFile) {
        Add-Content -Path $targetEnvFile -Value "`n# --- Appending $dbms-specific settings ---"
        Add-Content -Path $targetEnvFile -Value (Get-Content $addonFile)
    }

    Write-Host "Environment file '$targetEnvFile' created successfully with DBMS: $dbms."
}

exit 0