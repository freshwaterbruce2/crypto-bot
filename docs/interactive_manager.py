#!/usr/bin/env python3
"""
Interactive Documentation Manager - User-Controlled System
=========================================================

Addresses user concerns:
1. Sometimes AI gets cut off or overlooks something
2. User wants option to add to or take away from documentation
3. Need visible feedback when scripts run

Key Features:
- Interactive menu for full user control
- Manual review and editing of all documentation
- Visible output with confirmation prompts
- Add/remove capabilities for all documentation sections
"""

import json
import os
from datetime import datetime


class InteractiveDocManager:
    """User-controlled documentation management with manual override capabilities."""

    def __init__(self):
        self.project_root = "C:\\projects050625\\projects\\active\\tool-crypto-trading-bot-2025"
        self.docs_path = os.path.join(self.project_root, "docs", "development")

    def main_menu(self):
        """Interactive menu giving user full control over documentation."""
        while True:
            print("\n" + "="*60)
            print("INTERACTIVE DOCUMENTATION MANAGER")
            print("="*60)
            print("[1] View Current TODO Status")
            print("[2] Add New Task")
            print("[3] Mark Task as Completed")
            print("[4] Remove/Edit Task")
            print("[5] Add New Lesson Learned")
            print("[6] Add New Mistake Pattern")
            print("[7] View All Documentation")
            print("[8] Manual Sync & Backup")
            print("[9] Search Documentation")
            print("[0] Exit")
            print("="*60)

            choice = input("Choose option (0-9): ").strip()

            if choice == "1":
                self.view_todo_status()
            elif choice == "2":
                self.add_new_task()
            elif choice == "3":
                self.mark_task_completed()
            elif choice == "4":
                self.edit_remove_task()
            elif choice == "5":
                self.add_lesson_learned()
            elif choice == "6":
                self.add_mistake_pattern()
            elif choice == "7":
                self.view_all_docs()
            elif choice == "8":
                self.manual_sync_backup()
            elif choice == "9":
                self.search_documentation()
            elif choice == "0":
                print("[EXIT] Goodbye!")
                break
            else:
                print("[ERROR] Invalid choice. Please select 0-9.")

    def view_todo_status(self):
        """Display current TODO status with manual verification."""
        print("\n[TODO] Loading current task status...")

        todo_file = os.path.join(self.docs_path, "TODO_TRACKER.md")
        if not os.path.exists(todo_file):
            print("[ERROR] TODO_TRACKER.md not found")
            return

        with open(todo_file, encoding='utf-8') as f:
            content = f.read()

        # Count tasks by status
        completed = content.count('✅ COMPLETED')
        pending = content.count('🟡 PENDING')
        not_started = content.count('🔴 NOT STARTED')

        print("\n[STATUS] Current Task Summary:")
        print(f"  ✅ Completed: {completed}")
        print(f"  🟡 Pending: {pending}")
        print(f"  🔴 Not Started: {not_started}")

        if completed + pending + not_started > 0:
            completion_pct = round((completed / (completed + pending + not_started)) * 100, 1)
            print(f"  📊 Overall Progress: {completion_pct}%")

        view_detail = input("\n[PROMPT] View detailed task list? (y/n): ").lower()
        if view_detail == 'y':
            print("\n" + "="*50)
            print(content)
            print("="*50)

        input("\n[PROMPT] Press Enter to continue...")

    def add_new_task(self):
        """Add new task with user-defined priority and details."""
        print("\n[ADD_TASK] Adding new task to TODO tracker...")

        task_name = input("Task name: ").strip()
        if not task_name:
            print("[ERROR] Task name cannot be empty")
            return

        priority = input("Priority (HIGH/MEDIUM/LOW): ").strip().upper()
        if priority not in ['HIGH', 'MEDIUM', 'LOW']:
            priority = 'MEDIUM'

        description = input("Description: ").strip()
        files_affected = input("Files affected (optional): ").strip()
        time_estimate = input("Time estimate (optional): ").strip()

        # Generate task ID
        todo_file = os.path.join(self.docs_path, "TODO_TRACKER.md")
        with open(todo_file, encoding='utf-8') as f:
            content = f.read()

        # Find highest task number
        import re
        task_numbers = re.findall(r'Task #(\d+):', content)
        next_number = max([int(n) for n in task_numbers]) + 1 if task_numbers else 1

        # Create new task entry
        new_task = f"""
### **Task #{next_number}: {task_name}**
- **Status:** 🔴 NOT STARTED
- **Priority:** {priority}
- **Problem:** {description}
- **Files:** {files_affected if files_affected else 'TBD'}
- **Time Estimate:** {time_estimate if time_estimate else 'TBD'}
- **Success Criteria:** [To be defined]
"""

        # Add to TODO tracker
        with open(todo_file, 'a', encoding='utf-8') as f:
            f.write(new_task)

        print(f"[SUCCESS] Task #{next_number} added to TODO tracker")
        input("[PROMPT] Press Enter to continue...")

    def mark_task_completed(self):
        """Mark task as completed with user verification."""
        print("\n[COMPLETE_TASK] Marking task as completed...")

        todo_file = os.path.join(self.docs_path, "TODO_TRACKER.md")
        with open(todo_file, encoding='utf-8') as f:
            content = f.read()

        # Show pending tasks
        lines = content.split('\n')
        pending_tasks = []
        for i, line in enumerate(lines):
            if '🟡 PENDING' in line or '🔴 NOT STARTED' in line:
                # Find task number
                for j in range(max(0, i-3), min(len(lines), i+1)):
                    if 'Task #' in lines[j]:
                        pending_tasks.append((lines[j], i))
                        break

        if not pending_tasks:
            print("[INFO] No pending tasks found")
            input("[PROMPT] Press Enter to continue...")
            return

        print("\n[TASKS] Pending tasks:")
        for idx, (task_line, _) in enumerate(pending_tasks):
            print(f"  [{idx+1}] {task_line.strip()}")

        try:
            choice = int(input("\nSelect task to complete (number): ")) - 1
            if 0 <= choice < len(pending_tasks):
                task_line, line_idx = pending_tasks[choice]

                # Update status
                updated_content = content.replace(
                    '🟡 PENDING',
                    '✅ COMPLETED',
                    1
                ).replace(
                    '🔴 NOT STARTED',
                    '✅ COMPLETED',
                    1
                )

                # Write updated content
                with open(todo_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

                print("[SUCCESS] Task marked as completed")

                # Ask for completion notes
                notes = input("Completion notes (optional): ").strip()
                if notes:
                    print(f"[NOTES] {notes}")

            else:
                print("[ERROR] Invalid task selection")

        except ValueError:
            print("[ERROR] Please enter a valid number")

        input("[PROMPT] Press Enter to continue...")

    def edit_remove_task(self):
        """Edit or remove tasks with manual control."""
        print("\n[EDIT_TASK] Edit/Remove task...")

        todo_file = os.path.join(self.docs_path, "TODO_TRACKER.md")

        edit_choice = input("Do you want to (e)dit TODO file manually or (s)elect specific task? ").lower()

        if edit_choice == 'e':
            print("[EDIT] Opening TODO tracker for manual editing...")
            os.system(f'notepad "{todo_file}"')
        elif edit_choice == 's':
            print("[INFO] Feature to be implemented - manual editing recommended for now")
            os.system(f'notepad "{todo_file}"')

        input("[PROMPT] Press Enter to continue...")

    def add_lesson_learned(self):
        """Add new lesson learned with user input."""
        print("\n[ADD_LESSON] Adding new lesson learned...")

        title = input("Lesson title: ").strip()
        date_fixed = input("Date fixed (YYYY-MM-DD or 'today'): ").strip()
        if date_fixed.lower() == 'today':
            date_fixed = datetime.now().strftime('%Y-%m-%d')

        file_modified = input("File modified: ").strip()
        problem_desc = input("Problem description: ").strip()
        solution_desc = input("Solution description: ").strip()

        lesson_template = f"""
### **{title}**
**Date Fixed:** {date_fixed}
**File:** `{file_modified}`

#### **🚨 The Problem:**
{problem_desc}

#### **✅ The Solution:**
{solution_desc}

#### **🎯 Lesson Learned:**
[Add lesson learned summary here]

---
"""

        lessons_file = os.path.join(self.docs_path, "LESSONS_LEARNED.md")

        # Add to lessons learned file
        with open(lessons_file, 'a', encoding='utf-8') as f:
            f.write(lesson_template)

        print("[SUCCESS] Lesson added to LESSONS_LEARNED.md")

        edit_now = input("Edit lesson file now to add code examples? (y/n): ").lower()
        if edit_now == 'y':
            os.system(f'notepad "{lessons_file}"')

        input("[PROMPT] Press Enter to continue...")

    def add_mistake_pattern(self):
        """Add new mistake pattern to avoid."""
        print("\n[ADD_MISTAKE] Adding new mistake pattern...")

        pattern_type = input("Mistake category (e.g., 'Production Code', 'Exchange Integration'): ").strip()
        never_do = input("What to NEVER do: ").strip()
        always_do = input("What to ALWAYS do instead: ").strip()

        pattern_template = f"""
## {pattern_type.upper()} MISTAKES

### **❌ NEVER: {never_do}**
```python
# WRONG - Example of what NOT to do
# Add code example here
```

### **✅ ALWAYS: {always_do}**
```python
# CORRECT - Example of proper approach
# Add code example here
```

---
"""

        mistakes_file = os.path.join(self.docs_path, "MISTAKES_TO_AVOID.md")

        with open(mistakes_file, 'a', encoding='utf-8') as f:
            f.write(pattern_template)

        print("[SUCCESS] Mistake pattern added to MISTAKES_TO_AVOID.md")

        edit_now = input("Edit mistakes file now to add code examples? (y/n): ").lower()
        if edit_now == 'y':
            os.system(f'notepad "{mistakes_file}"')

        input("[PROMPT] Press Enter to continue...")

    def view_all_docs(self):
        """View all documentation files."""
        print("\n[VIEW_DOCS] Select document to view:")
        print("[1] TODO Tracker")
        print("[2] Lessons Learned")
        print("[3] Mistakes to Avoid")
        print("[4] All files (open in explorer)")

        choice = input("Choose (1-4): ").strip()

        if choice == "1":
            os.system(f'notepad "{os.path.join(self.docs_path, "TODO_TRACKER.md")}"')
        elif choice == "2":
            os.system(f'notepad "{os.path.join(self.docs_path, "LESSONS_LEARNED.md")}"')
        elif choice == "3":
            os.system(f'notepad "{os.path.join(self.docs_path, "MISTAKES_TO_AVOID.md")}"')
        elif choice == "4":
            os.system(f'explorer "{self.docs_path}"')

        input("[PROMPT] Press Enter to continue...")

    def manual_sync_backup(self):
        """Manual sync and backup with user control."""
        print("\n[SYNC] Manual synchronization and backup...")

        # Run backup
        backup_script = os.path.join(self.project_root, "backup_docs.bat")
        if os.path.exists(backup_script):
            print("[BACKUP] Running backup script...")
            os.system(f'"{backup_script}"')

        # Update session status
        print("[SYNC] Updating session status...")

        # Create simple status file
        status = {
            "last_updated": datetime.now().isoformat(),
            "user_notes": input("Add session notes (optional): ").strip(),
            "status": "Manual sync completed"
        }

        status_file = os.path.join(self.project_root, "docs", "manual_session_status.json")
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)

        print("[SUCCESS] Manual sync completed")
        print(f"[STATUS] Status saved to: {status_file}")

        input("[PROMPT] Press Enter to continue...")

    def search_documentation(self):
        """Search all documentation files."""
        print("\n[SEARCH] Searching documentation...")

        search_term = input("Enter search term: ").strip()
        if not search_term:
            return

        print(f"\n[RESULTS] Searching for '{search_term}'...")

        # Search all markdown files
        for filename in ["TODO_TRACKER.md", "LESSONS_LEARNED.md", "MISTAKES_TO_AVOID.md"]:
            filepath = os.path.join(self.docs_path, filename)
            if os.path.exists(filepath):
                with open(filepath, encoding='utf-8') as f:
                    content = f.read()

                if search_term.lower() in content.lower():
                    print(f"\n[FOUND] In {filename}:")
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if search_term.lower() in line.lower():
                            print(f"  Line {i+1}: {line.strip()}")

        input("\n[PROMPT] Press Enter to continue...")

if __name__ == "__main__":
    try:
        manager = InteractiveDocManager()
        manager.main_menu()
    except KeyboardInterrupt:
        print("\n[EXIT] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] {e}")
        input("[PROMPT] Press Enter to exit...")
