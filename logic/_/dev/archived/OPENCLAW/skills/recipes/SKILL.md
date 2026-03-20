---
name: recipes
description: End-to-end workflow recipes showing how to compose multiple tools for real tasks. Each recipe includes prerequisites, step sequence, error handling, and expected output.
---

# Multi-Tool Workflow Recipes

## How to Use Recipes

Before starting a multi-tool task:
1. Check if a recipe exists for this type of task
2. Follow the recipe's prerequisite checks
3. Execute steps in order, applying error recovery patterns
4. Report results using the recipe's output format

## Recipe 1: Bulk Messaging via CDMCP (WhatsApp/DingTalk/etc.)

**Task**: Send a message to multiple contacts.

**Prerequisites**:
```
1. Chrome running with --remote-debugging-port=9222
2. Target app tab open and authenticated
3. Message text prepared
```

**Steps**:
```
1. Verify auth:
   state = get_auth_state()
   assert state["authenticated"], "Not logged in"

2. Get contacts:
   contacts = get_chats()  # or get_contacts()
   
3. Filter contacts (optional):
   targets = [c for c in contacts if meets_criteria(c)]
   
4. Send with rate limiting:
   for i, contact in enumerate(targets):
       try:
           send_message(contact["id"], message_text)
           results["success"] += 1
       except Exception as e:
           results["failed"] += 1
           results["errors"].append(f"{contact['name']}: {e}")
       
       # Rate limit: 2-5 second delay between messages
       if i < len(targets) - 1:
           time.sleep(random.uniform(2, 5))
       
       # Progress report every 10 messages
       if (i + 1) % 10 == 0:
           print(f"Progress: {i+1}/{len(targets)}")

5. Report:
   print(f"Sent: {results['success']}, Failed: {results['failed']}")
   if results["errors"]:
       for err in results["errors"]:
           print(f"  - {err}")
```

**Error Recovery**:
- Rate limited? Wait 30s, then continue
- Tab closed? Use session recovery pattern
- Contact not found? Skip and log

---

## Recipe 2: CDMCP Session Bootstrap (Any Browser Tool)

**Task**: Boot a CDMCP session for any browser-based tool.

**Steps**:
```
1. Check Chrome CDP:
   from logic.chrome.session import is_chrome_cdp_available, CDP_PORT
   if not is_chrome_cdp_available():
       print("Start Chrome with: --remote-debugging-port=9222")
       return

2. Boot session (session-based tools like XMIND, YOUTUBE):
   result = boot_session()
   # This opens a tab, injects overlays, starts state machine

3. Or find existing tab (simple tools like GMAIL, SENTRY):
   tab = find_gmail_tab()
   if not tab:
       print("Open Gmail in Chrome first")
       return

4. Check auth:
   state = get_auth_state()
   if not state.get("authenticated"):
       print("Please log in to the app")
       return

5. Ready — execute operations
```

---

## Recipe 3: Data Collection from Multiple Sources

**Task**: Collect data from multiple web apps (e.g., project status from Asana + code metrics from Sentry + team activity from Linear).

**Steps**:
```
1. Boot/find tabs for each tool (can be parallel):
   asana_tab = find_asana_tab()
   sentry_tab = find_sentry_tab()
   linear_tab = find_linear_tab()
   
   missing = []
   if not asana_tab: missing.append("Asana")
   if not sentry_tab: missing.append("Sentry")
   if not linear_tab: missing.append("Linear")
   if missing:
       print(f"Open these in Chrome: {', '.join(missing)}")
       return

2. Collect data from each (sequential — one CDP session at a time):
   projects = list_projects()  # Asana
   issues = get_issues()       # Sentry
   user_info = get_user_info() # Linear

3. Combine and present:
   report = {
       "projects": len(projects),
       "open_issues": len([i for i in issues if i["status"] == "open"]),
       "team_members": user_info.get("team_count", "unknown"),
   }
   print(json.dumps(report, indent=2))
```

**Error Recovery**:
- One source fails? Report partial data from the others
- Auth expired on one? Re-authenticate just that one

---

## Recipe 4: Remote Code Execution via GCS

**Task**: Execute code on Google Colab and retrieve results.

**Prerequisites**:
```
1. Chrome running with CDP
2. Any Colab tab open (even the default welcome page)
3. GCS configured (run GCS --setup-tutorial if not)
```

**Steps**:
```
1. Check CDP:
   from logic.chrome.session import is_chrome_cdp_available
   assert is_chrome_cdp_available()

2. Find Colab tab:
   from tool.GOOGLE.logic.chrome.colab import find_colab_tab
   tab = find_colab_tab()
   assert tab, "Open a Colab tab in Chrome"

3. Inject and execute:
   from tool.GOOGLE.logic.chrome.colab import inject_and_execute
   result = inject_and_execute(code_string)
   
4. For file I/O, use GCS commands:
   GCS ls /content/drive/MyDrive/
   GCS cat /content/drive/MyDrive/output.txt
```

---

## Recipe 5: Tool Development Workflow

**Task**: Create, implement, test, and deploy a new tool.

**Steps**:
```
1. Scaffold:
   TOOL --dev create NEWTOOL
   # Creates tool/NEWTOOL/ with all template files

2. Implement logic:
   - Edit tool/NEWTOOL/logic/ — add domain logic
   - Edit tool/NEWTOOL/main.py — add CLI commands
   - Read logic/tool/template/AGENT.md for standard patterns

3. Add translations:
   - Edit tool/NEWTOOL/logic/_/translation/zh.json

4. Write tests:
   - Edit tool/NEWTOOL/test/test_01_basic.py
   
5. Run tests:
   TOOL --test NEWTOOL

6. Run quality audit:
   NEWTOOL --dev sanity-check

7. Deploy:
   NEWTOOL --setup
```

---

## Creating New Recipes

When you discover a new multi-tool workflow pattern:
1. Document it as a recipe in this file
2. Include: prerequisites, step sequence, error recovery, expected output
3. Test the recipe with a real execution
4. Record the recipe creation as a lesson: `SKILLS learn "Created recipe: <name>"`
