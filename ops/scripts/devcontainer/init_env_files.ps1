# Script to create .env (shared) and .env.STAGE files
# Called by VSCode devcontainer initializeCommand on Windows

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Determine ops directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$opsDir = Join-Path $scriptDir "../.."
$envDir = Join-Path $opsDir "env"
$templatesDir = Join-Path $opsDir "env-templates"

# Ensure env directory exists
if (-not (Test-Path $envDir)) {
    New-Item -ItemType Directory -Path $envDir -Force | Out-Null
}

# =============================================================================
# Interpolation function - replaces all known placeholders in content
# =============================================================================
function Invoke-TemplateInterpolation {
    param([string]$Content)

    # Stage and project
    $Content = $Content -replace '\{\{stage\}\}', $script:stageName
    $Content = $Content -replace '\{\{random_lower\}\}', $script:randomLower

    # Passwords and credentials
    $Content = $Content -replace '\{\{random_password\}\}', $script:iqAdminPwVal
    $Content = $Content -replace '\{\{db_super_user\}\}', $script:dbSuperUserVal
    $Content = $Content -replace '\{\{db_super_user_pw\}\}', $script:dbSuperUserPwVal
    $Content = $Content -replace '\{\{db_root_password\}\}', $script:dbRootPasswordVal
    $Content = $Content -replace '\{\{db_password\}\}', $script:dbPasswordVal

    # Database settings
    $Content = $Content -replace '\{\{dbms\}\}', $script:dbms
    $Content = $Content -replace '\{\{db_host\}\}', $script:dbHostVal
    $Content = $Content -replace '\{\{db_port\}\}', $script:dbPortVal

    # Dev-specific
    $Content = $Content -replace '\{\{uid\}\}', $script:currentUid
    $Content = $Content -replace '\{\{gid\}\}', $script:currentGid
    $Content = $Content -replace '\{\{vscode_settings_path\}\}', $script:vscodeSettingsPath

    return $Content
}

# Interpolate a template file and write to target
function Invoke-InterpolateFile {
    param(
        [string]$Source,
        [string]$Target
    )

    if (-not (Test-Path $Source)) {
        Write-Host "Warning: Template not found: $Source"
        return $false
    }

    $content = Get-Content $Source -Raw
    $content = Invoke-TemplateInterpolation -Content $content
    $content | Set-Content $Target
    return $true
}

# Append interpolated template content to a file
function Invoke-AppendInterpolated {
    param(
        [string]$Source,
        [string]$Target
    )

    if (-not (Test-Path $Source)) {
        return  # Silently skip if addon doesn't exist
    }

    $content = Get-Content $Source -Raw
    $content = Invoke-TemplateInterpolation -Content $content
    Add-Content -Path $Target -Value "`n$content"
}

# Support custom env file suffix (default: ".dev")
$envSuffix = if ($env:ENV_FILE_SUFFIX) { $env:ENV_FILE_SUFFIX } else { ".dev" }
$script:stageName = $envSuffix.TrimStart('.')

# Target files
$sharedEnvFile = Join-Path $envDir ".env"
$stageEnvFile = Join-Path $envDir ".env$envSuffix"

# Template files
$sharedTemplate = Join-Path $templatesDir "env.shared.template"
$stageTemplate = Join-Path $templatesDir "env.template"
$devAddonTemplate = Join-Path $templatesDir "env.dev.addon.template"

# --- Handle DBMS selection ---
$script:dbms = ""
if ($args.Count -gt 0) {
    $script:dbms = $args[0].ToLower()
} elseif ($env:DBMS) {
    $script:dbms = $env:DBMS.ToLower()
} else {
    $script:dbms = "postgres"
}

if ($script:dbms -ne "postgres" -and $script:dbms -ne "mariadb" -and $script:dbms -ne "sqlite") {
    Write-Host "Warning: Invalid DBMS ($script:dbms). Defaulting to postgres."
    $script:dbms = "postgres"
}

# DB host/port based on DBMS
$script:dbHostVal = ""
$script:dbPortVal = ""
switch ($script:dbms) {
    "postgres" { $script:dbHostVal = "db"; $script:dbPortVal = "5432" }
    "mariadb"  { $script:dbHostVal = "db"; $script:dbPortVal = "3306" }
    "sqlite"   { $script:dbHostVal = "localhost"; $script:dbPortVal = "" }
}

Write-Host "Stage: $script:stageName"
Write-Host "DBMS: $script:dbms"

# =============================================================================
# 1. Create shared .env if it doesn't exist
# =============================================================================

if (Test-Path $sharedEnvFile) {
    Write-Host "✓ Shared .env already exists"
} else {
    Write-Host "Creating shared .env..."
    if (Test-Path $sharedTemplate) {
        Copy-Item $sharedTemplate -Destination $sharedEnvFile
        Write-Host "✓ Created $sharedEnvFile"
    } else {
        Write-Host "Warning: Shared template not found: $sharedTemplate"
    }
}

# =============================================================================
# 2. Merge .env + .env.STAGE to compose/.env for Docker Compose
# =============================================================================
# Docker Compose needs .env in the project directory for ${VAR} substitution
# in YAML files (e.g., image: "${IQ_IMAGE}", COMPOSE_PROJECT_NAME).
# The env_file: directive only loads vars into container environment, not for YAML.
# We merge both files so all variables are available for interpolation.

$composeDir = Join-Path $opsDir "compose"
$composeEnvCopy = Join-Path $composeDir ".env"

# =============================================================================
# 3. Create stage-specific .env.STAGE if it doesn't exist
# =============================================================================

if (Test-Path $stageEnvFile) {
    Write-Host "✓ Stage file $stageEnvFile already exists"
} else {
    Write-Host "Creating $stageEnvFile..."

    # --- Gather required values (script scope for interpolation function) ---
    $script:currentUid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $script:currentGid = $script:currentUid  # Windows doesn't have GID like Unix

    # Generate random values
    $chars = 'abcdefghijklmnopqrstuvwxyz'
    $alphanumeric = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    $script:randomLower = -join ((0..4) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    $script:iqAdminPwVal = -join ((0..15) | ForEach-Object { $alphanumeric[(Get-Random -Maximum $alphanumeric.Length)] })
    $script:dbSuperUserVal = "ddl_user_" + (-join ((0..4) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] }))
    $script:dbSuperUserPwVal = -join ((0..15) | ForEach-Object { $alphanumeric[(Get-Random -Maximum $alphanumeric.Length)] })
    $script:dbRootPasswordVal = -join ((0..15) | ForEach-Object { $alphanumeric[(Get-Random -Maximum $alphanumeric.Length)] })
    $script:dbPasswordVal = -join ((0..15) | ForEach-Object { $alphanumeric[(Get-Random -Maximum $alphanumeric.Length)] })

    # VSCode settings path
    $script:vscodeSettingsPath = Join-Path $env:APPDATA "Code/User"
    if (-not (Test-Path $script:vscodeSettingsPath)) {
        $script:vscodeSettingsPath = "C:/temp/.vscode-host"
    }

    # --- Create from template using interpolation function ---
    Invoke-InterpolateFile -Source $stageTemplate -Target $stageEnvFile

    # --- Append DBMS-specific addon if exists ---
    $dbmsAddon = Join-Path $templatesDir "env.$script:dbms.addon.template"
    if (Test-Path $dbmsAddon) {
        Add-Content -Path $stageEnvFile -Value "`n# --- $script:dbms-specific settings ---"
        Invoke-AppendInterpolated -Source $dbmsAddon -Target $stageEnvFile
    }

    # --- Append dev-specific addon for dev stage ---
    if ($script:stageName -eq "dev") {
        Invoke-AppendInterpolated -Source $devAddonTemplate -Target $stageEnvFile
    }

    Write-Host "✓ Created $stageEnvFile"
}

# =============================================================================
# 4. Merge .env + .env.STAGE to compose/.env
# =============================================================================
# This merged file is needed for Docker Compose YAML interpolation.
# Variables like COMPOSE_PROJECT_NAME, IQ_IMAGE must be available during parsing.

if ((Test-Path $sharedEnvFile) -and (Test-Path $stageEnvFile)) {
    $header = @"
# =============================================================================
# AUTO-GENERATED MERGED FILE - DO NOT EDIT!
# =============================================================================
# Sources: ops/env/.env + ops/env/.env.$script:stageName
# This file is overwritten on every devcontainer start.
#
# Why this merged copy exists:
# Docker Compose needs .env in the project directory (ops/compose/) for
# `${VAR}` interpolation in YAML files (e.g., image: "`${IQ_IMAGE}`").
# Variables like COMPOSE_PROJECT_NAME are also read from here.
# The env_file: directive only loads vars into container environment.
#
# To change settings, edit: ops/env/.env or ops/env/.env.$script:stageName
# =============================================================================

# --- From ops/env/.env (shared) ---
"@
    $sharedContent = Get-Content $sharedEnvFile -Raw
    $stageHeader = "`n# --- From ops/env/.env.$script:stageName (stage-specific) ---`n"
    $stageContent = Get-Content $stageEnvFile -Raw

    $header + $sharedContent + $stageHeader + $stageContent | Set-Content $composeEnvCopy
    Write-Host "✓ Merged .env + .env.$script:stageName to compose/.env"
}

exit 0
