#!/usr/bin/env python3
"""
Setup dedicated git account for crypto trading bot project
"""

import subprocess
import os

def setup_git_config():
    """Setup git configuration for the dedicated account"""
    print("🔧 Setting up dedicated git account for crypto trading bot project")
    print("=" * 60)
    
    print("\n📝 Please provide your dedicated git account details:")
    
    # Get user input for git configuration
    username = input("Git username (for this project): ")
    email = input("Git email (for this project): ")
    
    if not username or not email:
        print("❌ Username and email are required")
        return False
    
    try:
        # Set local git config (only for this project)
        print(f"\n🔄 Configuring git for this project...")
        
        subprocess.run(['git', 'config', 'user.name', username], check=True)
        subprocess.run(['git', 'config', 'user.email', email], check=True)
        
        print(f"✅ Git configured:")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        
        # Show current config
        print(f"\n📋 Current git configuration:")
        result = subprocess.run(['git', 'config', '--list', '--local'], 
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'user.' in line:
                print(f"   {line}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error configuring git: {e}")
        return False

def create_initial_commit():
    """Create initial commit with current state"""
    print(f"\n📦 Creating initial commit...")
    
    try:
        # Add all files
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Create initial commit
        commit_message = """Initial commit: Crypto Trading Bot Project

- Core trading bot with Kraken integration
- Agent tools bridge for automated repairs
- Optimization and verification systems
- Self-learning and autonomous repair capabilities
- Emergency repair agents and validation systems

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        
        print("✅ Initial commit created successfully")
        
        # Show commit info
        result = subprocess.run(['git', 'log', '--oneline', '-1'], 
                              capture_output=True, text=True)
        print(f"   Commit: {result.stdout.strip()}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating commit: {e}")
        return False

def setup_remote_instructions():
    """Provide instructions for setting up remote repository"""
    print(f"\n🌐 Setting up remote repository (GitHub/GitLab):")
    print("=" * 50)
    print("1. Create a new repository on GitHub/GitLab with your dedicated account")
    print("2. Copy the repository URL (HTTPS or SSH)")
    print("3. Run: git remote add origin <repository-url>")
    print("4. Run: git push -u origin master")
    print("\nExample:")
    print("   git remote add origin https://github.com/username/crypto-trading-bot.git")
    print("   git push -u origin master")

def main():
    """Main setup function"""
    print("🚀 CRYPTO TRADING BOT - GIT SETUP")
    print("=" * 60)
    
    # Setup git config
    if setup_git_config():
        print("\n" + "=" * 60)
        
        # Create initial commit
        if create_initial_commit():
            print("\n" + "=" * 60)
            
            # Show remote setup instructions
            setup_remote_instructions()
            
            print("\n✅ Git setup complete for crypto trading bot project!")
            print("📁 All files are now version controlled")
            print("🔄 Ready to push to your dedicated remote repository")
        else:
            print("❌ Failed to create initial commit")
    else:
        print("❌ Failed to setup git configuration")

if __name__ == '__main__':
    main()