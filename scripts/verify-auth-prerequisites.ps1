[CmdletBinding()]
param(
    [switch]$Online,
    [string]$ExpectedProjectRef = "diiestlnmpaarhhexwhi",
    [int]$ExpectedAdminCount = 2,
    [switch]$RequireNormalUser
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path "$PSScriptRoot\.."
$envPath = Join-Path $repoRoot ".env"
$failures = 0
$warnings = 0

function Write-Check {
    param(
        [ValidateSet("PASS", "WARN", "FAIL")]
        [string]$Status,
        [string]$Name,
        [string]$Detail = ""
    )

    if ($Status -eq "FAIL") {
        $script:failures += 1
    } elseif ($Status -eq "WARN") {
        $script:warnings += 1
    }

    $suffix = if ($Detail) { ": $Detail" } else { "" }
    Write-Host "[$Status] $Name$suffix"
}

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")
        if ($name) {
            $values[$name] = $value
        }
    }
    return $values
}

function Split-EmailList {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return @()
    }
    return @(
        $Value -split "[,;\s]+" |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { $_.Trim().ToLowerInvariant() }
    )
}

Write-Host "OryxenAI auth prerequisite verification (secret values are never printed)"

if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    Write-Check FAIL ".env exists"
    exit 1
}
Write-Check PASS ".env exists"

$values = Read-DotEnv $envPath
$required = @(
    "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_SECRET_KEY",
    "ORYXENAI_ADMIN_BOOTSTRAP_EMAILS",
    "ORYXENAI_ALLOWED_USER_EMAILS"
)

foreach ($name in $required) {
    if (-not $values.ContainsKey($name)) {
        Write-Check FAIL "$name declared"
        continue
    }

    if ($name -eq "ORYXENAI_ALLOWED_USER_EMAILS") {
        Write-Check PASS "$name declared"
        continue
    }

    if ([string]::IsNullOrWhiteSpace([string]$values[$name])) {
        Write-Check FAIL "$name nonempty"
    } else {
        Write-Check PASS "$name nonempty"
    }
}

if ($values.ContainsKey("SUPABASE_URL") -and $ExpectedProjectRef) {
    $expectedUrl = "https://$ExpectedProjectRef.supabase.co"
    $actualUrl = ([string]$values["SUPABASE_URL"]).TrimEnd("/")
    if ($actualUrl -eq $expectedUrl) {
        Write-Check PASS "Supabase URL matches expected project"
    } else {
        Write-Check FAIL "Supabase URL matches expected project"
    }
}

$admins = Split-EmailList ([string]$values["ORYXENAI_ADMIN_BOOTSTRAP_EMAILS"])
$distinctAdmins = @($admins | Select-Object -Unique)
if ($admins.Count -eq $ExpectedAdminCount -and $distinctAdmins.Count -eq $ExpectedAdminCount) {
    Write-Check PASS "bootstrap administrator count" "$ExpectedAdminCount distinct entries"
} else {
    Write-Check FAIL "bootstrap administrator count" "expected $ExpectedAdminCount distinct entries"
}

$allowedUsers = Split-EmailList ([string]$values["ORYXENAI_ALLOWED_USER_EMAILS"])
$distinctAllowedUsers = @($allowedUsers | Select-Object -Unique)
if ($allowedUsers.Count -ne $distinctAllowedUsers.Count) {
    Write-Check FAIL "normal-user allowlist uniqueness"
} else {
    Write-Check PASS "normal-user allowlist uniqueness" "$($distinctAllowedUsers.Count) entries"
}

$overlap = @($distinctAllowedUsers | Where-Object { $distinctAdmins -contains $_ })
if ($overlap.Count -eq 0) {
    Write-Check PASS "admin and normal allowlists do not overlap"
} else {
    Write-Check FAIL "admin and normal allowlists do not overlap"
}

if ($distinctAllowedUsers.Count -gt 15) {
    Write-Check FAIL "normal-user allowlist within policy" "maximum is 15"
} elseif ($distinctAllowedUsers.Count -eq 0) {
    $status = if ($RequireNormalUser) { "FAIL" } else { "WARN" }
    Write-Check $status "normal test identity configured" "pending by owner decision"
} else {
    Write-Check PASS "normal-user allowlist within policy" "$($distinctAllowedUsers.Count) of 15"
}

if ($Online -and $failures -eq 0) {
    $baseUrl = ([string]$values["SUPABASE_URL"]).TrimEnd("/")
    $publishableKey = [string]$values["SUPABASE_PUBLISHABLE_KEY"]
    $headers = @{ apikey = $publishableKey }

    try {
        $settings = Invoke-RestMethod `
            -Uri "$baseUrl/auth/v1/settings" `
            -Headers $headers `
            -Method Get `
            -TimeoutSec 20
        Write-Check PASS "Supabase Auth settings reachable"
        if ($null -ne $settings.external -and [bool]$settings.external.google) {
            Write-Check PASS "Google provider enabled"
        } else {
            Write-Check FAIL "Google provider enabled"
        }
    } catch {
        Write-Check FAIL "Supabase Auth settings reachable" $_.Exception.GetType().Name
    }

    try {
        $jwks = Invoke-RestMethod `
            -Uri "$baseUrl/auth/v1/.well-known/jwks.json" `
            -Method Get `
            -TimeoutSec 20
        $keyCount = @($jwks.keys).Count
        if ($keyCount -gt 0) {
            Write-Check PASS "Supabase JWKS available" "$keyCount public signing key(s)"
        } else {
            Write-Check FAIL "Supabase JWKS available" "no asymmetric signing key exposed"
        }
    } catch {
        Write-Check FAIL "Supabase JWKS available" $_.Exception.GetType().Name
    }

    try {
        Add-Type -AssemblyName System.Net.Http
        $redirect = [uri]::EscapeDataString("http://localhost:8000/auth/callback")
        $authorizeUri = "$baseUrl/auth/v1/authorize?provider=google&redirect_to=$redirect"
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.AllowAutoRedirect = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        try {
            $client.DefaultRequestHeaders.Add("apikey", $publishableKey)
            $response = $client.GetAsync($authorizeUri).GetAwaiter().GetResult()
            $statusCode = [int]$response.StatusCode
            $locationHost = ""
            if ($null -ne $response.Headers.Location) {
                $locationHost = $response.Headers.Location.Host
            }
            if ($statusCode -in @(302, 303, 307, 308) -and $locationHost -eq "accounts.google.com") {
                Write-Check PASS "Google OAuth initiation" "redirects to Google"
            } else {
                Write-Check FAIL "Google OAuth initiation" "unexpected redirect outcome"
            }
        } finally {
            $client.Dispose()
            $handler.Dispose()
        }
    } catch {
        Write-Check FAIL "Google OAuth initiation" $_.Exception.GetType().Name
    }
} elseif ($Online) {
    Write-Check WARN "online checks skipped" "fix local prerequisite failures first"
} else {
    Write-Check WARN "online checks not requested" "rerun with -Online"
}

Write-Host ""
Write-Host "Result: $failures failure(s), $warnings warning(s)."
if ($failures -gt 0) {
    exit 1
}
exit 0
