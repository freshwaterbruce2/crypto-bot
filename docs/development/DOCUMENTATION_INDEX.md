# 📁 DOCUMENTATION INDEX - QUICK ACCESS GUIDE

## 🎯 DOCUMENT LOCATIONS

### **📋 Development Docs**
```
C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs\development\
├── LESSONS_LEARNED.md      - Critical fixes with exact code solutions
├── TODO_TRACKER.md         - Task progress and completion status  
├── MISTAKES_TO_AVOID.md    - Quick reference checklist
└── DOCUMENTATION_INDEX.md  - This file (navigation guide)
```

### **🚀 Quick Access Commands**
```batch
:: Open docs folder
explorer "C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs\development"

:: Quick edit TODO tracker
notepad "C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs\development\TODO_TRACKER.md"

:: Reference mistakes checklist  
type "C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs\development\MISTAKES_TO_AVOID.md"
```

## 📝 **DAILY UPDATE WORKFLOW**

### **Before Coding Session:**
1. Open `MISTAKES_TO_AVOID.md` → Review checklist
2. Check `TODO_TRACKER.md` → See current tasks
3. Keep both files open in separate tabs

### **After Fixing Bugs:**
1. Update `LESSONS_LEARNED.md` → Add new fixes with exact code
2. Update `TODO_TRACKER.md` → Mark tasks as completed
3. Run backup script (see below)

## 💾 **SIMPLE BACKUP STRATEGY**

### **Automatic Daily Backup Script:**
```batch
@echo off
set SOURCE="C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs"
set BACKUP="C:\projects050625\backups\trading-bot-docs_%date:~-4,4%-%date:~-10,2%-%date:~-7,2%"
robocopy %SOURCE% %BACKUP% /E /XO
echo Docs backed up to %BACKUP%
```

Save as: `backup_docs.bat` and run daily.

## 🔍 **SEARCH YOUR DOCS**

### **Find specific fixes:**
```batch
findstr /S /I "autonomous sell engine" "C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs\*.md"
findstr /S /I "fake profit" "C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs\*.md"
```

### **Find incomplete tasks:**
```batch
findstr /S /I "PENDING" "C:\projects050625\projects\active\tool-crypto-trading-bot-2025\docs\development\TODO_TRACKER.md"
```

---

*Keep this index open for instant navigation to your documentation.*