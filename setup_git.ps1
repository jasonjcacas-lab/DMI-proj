# Git Setup Script for DMI Tool Project
# Run this script after installing Git

Write-Host "Setting up Git repository for DMI Tool..." -ForegroundColor Green

# Check if git is available
try {
    git --version | Out-Null
    Write-Host "Git is installed!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Git is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "Or install GitHub Desktop from: https://desktop.github.com/" -ForegroundColor Yellow
    exit 1
}

# Initialize git repository if not already initialized
if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Cyan
    git init
} else {
    Write-Host "Git repository already initialized." -ForegroundColor Yellow
}

# Set up remote (you may need to configure credentials)
Write-Host "Setting up remote repository..." -ForegroundColor Cyan
$remoteUrl = "https://github.com/jasonjcacas-lab/DMI-proj.git"

# Check if remote already exists
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    Write-Host "Remote 'origin' already exists: $existingRemote" -ForegroundColor Yellow
    $change = Read-Host "Do you want to change it to $remoteUrl? (y/n)"
    if ($change -eq "y") {
        git remote set-url origin $remoteUrl
        Write-Host "Remote URL updated!" -ForegroundColor Green
    }
} else {
    git remote add origin $remoteUrl
    Write-Host "Remote 'origin' added!" -ForegroundColor Green
}

# Stage all files
Write-Host "Staging files..." -ForegroundColor Cyan
git add .

# Check if there are changes to commit
$status = git status --porcelain
if ($status) {
    Write-Host "Creating initial commit..." -ForegroundColor Cyan
    git commit -m "Initial commit: DMI Tool project"
    Write-Host "Commit created!" -ForegroundColor Green
    
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Configure Git user (if not already done):" -ForegroundColor White
    Write-Host "   git config --global user.name 'Your Name'" -ForegroundColor Gray
    Write-Host "   git config --global user.email 'your.email@example.com'" -ForegroundColor Gray
    Write-Host "`n2. Push to GitHub:" -ForegroundColor White
    Write-Host "   git push -u origin main" -ForegroundColor Gray
    Write-Host "   (or 'git push -u origin master' if your default branch is master)" -ForegroundColor Gray
    Write-Host "`nNote: You may be prompted for GitHub credentials." -ForegroundColor Yellow
    Write-Host "If you use two-factor authentication, use a Personal Access Token as password." -ForegroundColor Yellow
} else {
    Write-Host "No changes to commit. Repository is up to date." -ForegroundColor Yellow
}

Write-Host "`nSetup complete!" -ForegroundColor Green

