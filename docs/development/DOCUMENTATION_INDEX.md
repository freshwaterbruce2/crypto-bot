# 📁 DOCUMENTATION INDEX - QUICK ACCESS GUIDE

## 🎯 DOCUMENT LOCATIONS

### **📋 Development Docs**
```
/mnt/c/dev/tools/crypto-trading-bot-2025/docs/development/
├── LESSONS_LEARNED.md      - Critical fixes with exact code solutions
├── TODO_TRACKER.md         - Task progress and completion status  
├── MISTAKES_TO_AVOID.md    - Quick reference checklist
└── DOCUMENTATION_INDEX.md  - This file (navigation guide)
```

### **🚀 Quick Access Commands**
```bash
# Open docs folder (Windows)
explorer /mnt/c/dev/tools/crypto-trading-bot-2025/docs/development

# Open docs folder (WSL)
cd /mnt/c/dev/tools/crypto-trading-bot-2025/docs/development

# Quick edit TODO tracker
nano /mnt/c/dev/tools/crypto-trading-bot-2025/docs/development/TODO_TRACKER.md

# Reference mistakes checklist  
cat /mnt/c/dev/tools/crypto-trading-bot-2025/docs/development/MISTAKES_TO_AVOID.md
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
```bash
#!/bin/bash
SOURCE="/mnt/c/dev/tools/crypto-trading-bot-2025/docs"
BACKUP="/mnt/c/dev/tools/crypto-trading-bot-2025/backups/docs_$(date +%Y-%m-%d)"
mkdir -p "$(dirname "$BACKUP")"
cp -r "$SOURCE" "$BACKUP"
echo "Docs backed up to $BACKUP"
```

Save as: `backup_docs.sh`, make executable with `chmod +x backup_docs.sh`, and run daily.

## 🔍 **SEARCH YOUR DOCS**

### **Find specific fixes:**
```bash
grep -r -i "autonomous sell engine" /mnt/c/dev/tools/crypto-trading-bot-2025/docs/*.md
grep -r -i "fake profit" /mnt/c/dev/tools/crypto-trading-bot-2025/docs/*.md
```

### **Find incomplete tasks:**
```bash
grep -i "PENDING" /mnt/c/dev/tools/crypto-trading-bot-2025/docs/development/TODO_TRACKER.md
```

---

*Keep this index open for instant navigation to your documentation.*