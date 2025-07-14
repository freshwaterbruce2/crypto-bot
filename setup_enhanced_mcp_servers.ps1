# Enhanced MCP Server Setup for Cryptocurrency Trading Bot
# Focused on decimal precision math and Desktop Commander functionality

Write-Host "🚀 Setting up Enhanced MCP Servers for Cryptocurrency Trading..." -ForegroundColor Green

# Create extensions directory if it doesn't exist
$extensionsPath = "C:\projects050625\projects\active\tool-crypto-trading-bot-2025\extensions"
if (!(Test-Path $extensionsPath)) {
    New-Item -ItemType Directory -Path $extensionsPath -Force
}

# Change to extensions directory
Set-Location $extensionsPath

Write-Host "📦 Installing Essential MCP Servers..." -ForegroundColor Yellow

# 1. Desktop Commander for Windows 11
Write-Host "🖥️ Installing Desktop Commander..." -ForegroundColor Cyan
if (!(Test-Path "desktop-commander")) {
    git clone https://github.com/modelcontextprotocol/servers.git temp-servers
    if (Test-Path "temp-servers\src\desktop") {
        Move-Item "temp-servers\src\desktop" "desktop-commander"
        Remove-Item "temp-servers" -Recurse -Force
    } else {
        Write-Host "⚠️ Desktop Commander not found in repo, creating manual implementation..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path "desktop-commander" -Force
    }
}

# 2. Math Calculator with Decimal Support
Write-Host "🧮 Installing Math Calculator with Decimal Precision..." -ForegroundColor Cyan
if (!(Test-Path "math-calculator")) {
    New-Item -ItemType Directory -Path "math-calculator" -Force
}

# 3. Technical Analysis Tools
Write-Host "📊 Installing Technical Analysis MCP..." -ForegroundColor Cyan
npm install -g @modelcontextprotocol/server-sequential-thinking

# 4. Puppeteer for Web Automation
Write-Host "🤖 Installing Puppeteer MCP..." -ForegroundColor Cyan
npm install -g @modelcontextprotocol/server-puppeteer

# 5. GitHub Integration
Write-Host "📚 Installing GitHub MCP..." -ForegroundColor Cyan
npm install -g @modelcontextprotocol/server-github

# 6. Everything Search (Windows file search)
Write-Host "🔍 Installing Everything Search MCP..." -ForegroundColor Cyan
if (!(Test-Path "everything-search")) {
    New-Item -ItemType Directory -Path "everything-search" -Force
}

# 7. Windows System Info
Write-Host "🖥️ Installing Windows System Info MCP..." -ForegroundColor Cyan
if (!(Test-Path "windows-system")) {
    New-Item -ItemType Directory -Path "windows-system" -Force
}

# 8. Crypto News and Data
Write-Host "📰 Installing Crypto News MCP..." -ForegroundColor Cyan
if (!(Test-Path "crypto-news")) {
    New-Item -ItemType Directory -Path "crypto-news" -Force
}

Write-Host "✅ MCP Server Installation Complete!" -ForegroundColor Green
Write-Host "📝 Next: Creating custom implementations and updating config..." -ForegroundColor Yellow
