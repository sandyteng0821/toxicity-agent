# Database Usage Guide (v1.1.0)

**Version**: v1.1.0  
**Last Updated**: 2024-11-17

This guide covers the two databases used in the Toxicity Agent:
1. **Chat Memory Database** (`chat_memory.db`) - Conversation history
2. **Toxicity Data Database** (`toxicity_data.db`) - JSON versioning

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Chat Memory Database](#chat-memory-database)
- [Toxicity Data Database](#toxicity-data-database)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

```bash
# SQLite3 (usually pre-installed on macOS/Linux)
sqlite3 --version

# If not installed:
# macOS
brew install sqlite3

# Ubuntu/Debian
sudo apt-get install sqlite3

# Windows
# Download from: https://www.sqlite.org/download.html
```

### Optional Tools

**DB Browser for SQLite** (Recommended GUI)
```bash
# macOS
brew install --cask db-browser-for-sqlite

# Or download from: https://sqlitebrowser.org/
```

**Python** (for programmatic access)
```bash
python3 --version  # Should be 3.9+
```

---

## Quick Start

### 1. Check if Databases Exist

```bash
# From project root
ls -lh *.db

# Expected output:
# chat_memory.db       # Chat history (managed by LangGraph)
# toxicity_data.db     # JSON versions (managed by ToxicityDB)
```

### 2. View Database Contents

```bash
# Chat memory (quick peek)
sqlite3 chat_memory.db ".tables"

# Toxicity data (quick peek)
sqlite3 toxicity_data.db "SELECT conversation_id, version, modification_summary FROM toxicity_versions LIMIT 5;"
```

### 3. Open in GUI

```bash
# Open both databases
open -a "DB Browser for SQLite" chat_memory.db
open -a "DB Browser for SQLite" toxicity_data.db
```

---

## Chat Memory Database

### Overview

**File**: `chat_memory.db`  
**Purpose**: Store conversation state and checkpoints  
**Managed By**: LangGraph's `SqliteSaver`  
**Access**: Read-only (automated by LangGraph)

### Database Schema

```sql
-- Checkpoints table (managed by LangGraph)
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BLOB,
    metadata BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Writes table (for checkpoint metadata)
CREATE TABLE writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

### How It Works

```python
# When you invoke the graph with a thread_id:
config = {"configurable": {"thread_id": "conv-abc-123"}}
result = graph.invoke(state, config=config)

# LangGraph automatically:
# 1. Loads previous checkpoint (if exists)
# 2. Executes workflow
# 3. Saves new checkpoint with updated state
```

### Viewing Chat History

#### Using SQLite CLI

```bash
sqlite3 chat_memory.db

# List all thread IDs
.mode column
.headers on
SELECT DISTINCT thread_id, COUNT(*) as checkpoints 
FROM checkpoints 
GROUP BY thread_id;

# View checkpoints for specific thread
SELECT checkpoint_id, parent_checkpoint_id, type 
FROM checkpoints 
WHERE thread_id = 'your-thread-id' 
ORDER BY checkpoint_id;

# Exit
.quit
```

#### Using Python

```python
# view_chat_history.py
import sqlite3
import pickle
from pprint import pprint

def view_chat_checkpoints(thread_id=None):
    """View chat memory checkpoints"""
    conn = sqlite3.connect("chat_memory.db")
    cursor = conn.cursor()
    
    if thread_id:
        # View specific thread
        cursor.execute("""
            SELECT checkpoint_id, checkpoint, metadata
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY checkpoint_id
        """, (thread_id,))
    else:
        # View all threads
        cursor.execute("""
            SELECT thread_id, COUNT(*) as num_checkpoints
            FROM checkpoints
            GROUP BY thread_id
        """)
        print("Available threads:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]} checkpoints")
        conn.close()
        return
    
    print(f"\nCheckpoints for thread: {thread_id}\n")
    print("=" * 80)
    
    for checkpoint_id, checkpoint_blob, metadata_blob in cursor.fetchall():
        print(f"\nCheckpoint ID: {checkpoint_id}")
        
        # Deserialize checkpoint (contains state)
        try:
            checkpoint = pickle.loads(checkpoint_blob)
            print("State keys:", list(checkpoint.get('channel_values', {}).keys()))
            
            # Show specific fields if they exist
            values = checkpoint.get('channel_values', {})
            if 'json_data' in values:
                inci = values['json_data'].get('inci', 'N/A')
                print(f"  INCI: {inci}")
            if 'user_input' in values:
                print(f"  User Input: {values['user_input'][:100]}...")
            if 'response' in values:
                print(f"  Response: {values['response'][:100]}...")
        except Exception as e:
            print(f"  (Unable to deserialize: {e})")
        
        print("-" * 80)
    
    conn.close()

if __name__ == "__main__":
    # List all threads
    view_chat_checkpoints()
    
    # View specific thread (uncomment and provide thread_id)
    # view_chat_checkpoints("your-thread-id-here")
```

**Usage:**
```bash
python view_chat_history.py
```

### ⚠️ Important Notes

- **DO NOT** manually modify `chat_memory.db`
- Checkpoints are automatically managed by LangGraph
- Binary data (BLOB) requires deserialization to view
- Each thread_id represents one conversation

---

## Toxicity Data Database

### Overview

**File**: `toxicity_data.db`  
**Purpose**: Store JSON data versions with audit trail  
**Managed By**: `ToxicityDB` class (`core/database.py`)  
**Access**: Read/Write via ToxicityDB API

### Database Schema

```sql
-- Toxicity versions table
CREATE TABLE toxicity_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL,
    data TEXT NOT NULL,              -- Full JSON as string
    modification_summary TEXT,        -- Human-readable summary
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(conversation_id, version)
);

-- Index for fast conversation lookup
CREATE INDEX idx_conversation_id ON toxicity_versions(conversation_id);
```

**Field Descriptions:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | INTEGER | Auto-increment primary key | 1, 2, 3, ... |
| `conversation_id` | VARCHAR(100) | Links to conversation | "conv-abc-123" |
| `version` | INTEGER | Version number (1-based) | 1, 2, 3, ... |
| `data` | TEXT | Complete JSON snapshot | `{"inci": "L-MENTHOL", ...}` |
| `modification_summary` | TEXT | What changed | "Updated NOAEL to 200" |
| `created_at` | DATETIME | Timestamp | "2024-11-17 10:30:00" |

### How It Works

```python
# When you edit via API:
POST /api/edit
{
  "instruction": "Set NOAEL to 200",
  "inci_name": "L-MENTHOL"
}

# System:
# 1. Loads current version (or creates version 1)
# 2. Applies LLM modifications
# 3. Saves new version with incremented number
# 4. Returns updated data + version number
```

### Viewing Toxicity Data

#### Using SQLite CLI

```bash
sqlite3 toxicity_data.db

# Setup nice formatting
.mode column
.headers on
.width 15 8 30 20

# View all versions
SELECT conversation_id, version, modification_summary, created_at 
FROM toxicity_versions 
ORDER BY created_at DESC;

# View specific conversation
SELECT version, modification_summary, created_at
FROM toxicity_versions
WHERE conversation_id = 'your-conversation-id'
ORDER BY version;

# Get latest version for each conversation
SELECT t1.*
FROM toxicity_versions t1
INNER JOIN (
    SELECT conversation_id, MAX(version) as max_version
    FROM toxicity_versions
    GROUP BY conversation_id
) t2 ON t1.conversation_id = t2.conversation_id 
    AND t1.version = t2.max_version;

# Statistics
SELECT 
    COUNT(DISTINCT conversation_id) as num_conversations,
    COUNT(*) as total_versions,
    MAX(version) as max_version
FROM toxicity_versions;

# Exit
.quit
```

#### Using Python (ToxicityDB API)

```python
# view_toxicity_data.py
from core.database import ToxicityDB
import json

def view_all_conversations():
    """List all conversations"""
    db = ToxicityDB()
    
    with db.session_scope() as session:
        from sqlalchemy import func
        from core.database import ToxicityVersion
        
        # Get all unique conversation IDs
        conversations = session.query(
            ToxicityVersion.conversation_id,
            func.max(ToxicityVersion.version).label('latest_version'),
            func.count(ToxicityVersion.id).label('num_versions')
        ).group_by(ToxicityVersion.conversation_id).all()
        
        print("Available Conversations:")
        print("=" * 80)
        for conv_id, latest_ver, num_vers in conversations:
            print(f"  {conv_id}")
            print(f"    Latest version: {latest_ver}")
            print(f"    Total versions: {num_vers}")
            print()

def view_conversation_history(conversation_id):
    """View all versions of a conversation"""
    db = ToxicityDB()
    
    history = db.get_modification_history(conversation_id)
    
    print(f"\nHistory for: {conversation_id}")
    print("=" * 80)
    
    for entry in history:
        print(f"\nVersion {entry['version']} ({entry['created_at']})")
        print(f"Summary: {entry['modification_summary']}")
        
        # Parse JSON data
        data = json.loads(entry['data'])
        print(f"INCI: {data.get('inci', 'N/A')}")
        print(f"Category: {data.get('category', 'N/A')}")
        print(f"NOAEL entries: {len(data.get('NOAEL', []))}")
        print(f"DAP entries: {len(data.get('DAP', []))}")
        print("-" * 80)

def view_current_version(conversation_id):
    """View latest version"""
    db = ToxicityDB()
    
    version = db.get_current_version(conversation_id)
    
    if not version:
        print(f"No data found for: {conversation_id}")
        return
    
    print(f"\nCurrent Version: {version.version}")
    print(f"Last Modified: {version.created_at}")
    print(f"Summary: {version.modification_summary}")
    print("\nData:")
    
    data = json.loads(version.data)
    print(json.dumps(data, indent=2))

def compare_versions(conversation_id, from_version, to_version):
    """Compare two versions"""
    db = ToxicityDB()
    
    diff = db.get_diff(conversation_id, from_version, to_version)
    
    print(f"\nDiff from v{from_version} to v{to_version}:")
    print("=" * 80)
    
    for change in diff:
        change_type, path, values = change
        print(f"{change_type.upper()}: {'.'.join(map(str, path))}")
        if change_type == 'change':
            print(f"  Old: {values[0]}")
            print(f"  New: {values[1]}")
        elif change_type == 'add':
            print(f"  Added: {values}")
        elif change_type == 'remove':
            print(f"  Removed: {values}")
        print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        # No arguments - show all conversations
        view_all_conversations()
    elif len(sys.argv) == 2:
        # One argument - show conversation history
        view_conversation_history(sys.argv[1])
    elif len(sys.argv) == 4 and sys.argv[1] == "diff":
        # Diff mode: python script.py diff conv-id from-ver to-ver
        compare_versions(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    else:
        print("Usage:")
        print("  python view_toxicity_data.py                    # List all")
        print("  python view_toxicity_data.py <conversation_id>  # View history")
        print("  python view_toxicity_data.py diff <conv_id> <from_ver> <to_ver>  # Compare")
```

**Usage:**
```bash
# List all conversations
python view_toxicity_data.py

# View specific conversation history
python view_toxicity_data.py conv-abc-123

# Compare versions
python view_toxicity_data.py diff conv-abc-123 1 3
```

### Programmatic Access (API)

```python
# In your code
from core.database import ToxicityDB
import json

db = ToxicityDB()

# Save new version
db.save_version(
    conversation_id="conv-abc-123",
    data={"inci": "L-MENTHOL", "NOAEL": [...]},
    modification_summary="Updated NOAEL to 200 mg/kg bw/day"
)

# Get current version
current = db.get_current_version("conv-abc-123")
data = json.loads(current.data)
print(f"Current INCI: {data['inci']}")
print(f"Version: {current.version}")

# Get full history
history = db.get_modification_history("conv-abc-123")
for entry in history:
    print(f"v{entry['version']}: {entry['modification_summary']}")

# Compare versions
diff = db.get_diff("conv-abc-123", from_version=1, to_version=3)
print(f"Changes: {len(diff)}")
```

---

## Common Operations

### Export Data

#### Export to JSON

```bash
# Export all toxicity data
sqlite3 toxicity_data.db <<EOF
.mode json
.output toxicity_export.json
SELECT * FROM toxicity_versions;
.quit
EOF

# Export specific conversation
sqlite3 toxicity_data.db <<EOF
.mode json
.output conversation_export.json
SELECT * FROM toxicity_versions WHERE conversation_id='conv-abc-123';
.quit
EOF
```

#### Export to CSV

```bash
sqlite3 toxicity_data.db <<EOF
.mode csv
.headers on
.output toxicity_export.csv
SELECT conversation_id, version, modification_summary, created_at FROM toxicity_versions;
.quit
EOF
```

### Backup Databases

```bash
# Backup both databases
cp chat_memory.db chat_memory_backup_$(date +%Y%m%d).db
cp toxicity_data.db toxicity_data_backup_$(date +%Y%m%d).db

# Or use SQLite backup command
sqlite3 toxicity_data.db ".backup toxicity_data_backup.db"
```

### Clean Old Data

```python
# clean_old_data.py
from core.database import ToxicityDB
from datetime import datetime, timedelta

db = ToxicityDB()

with db.session_scope() as session:
    from core.database import ToxicityVersion
    
    # Delete versions older than 90 days (keep latest per conversation)
    cutoff_date = datetime.now() - timedelta(days=90)
    
    # Get latest versions (to keep)
    latest_versions = session.query(
        ToxicityVersion.conversation_id,
        func.max(ToxicityVersion.version)
    ).group_by(ToxicityVersion.conversation_id).all()
    
    # Delete old versions except latest
    deleted_count = 0
    for conv_id, latest_ver in latest_versions:
        result = session.query(ToxicityVersion).filter(
            ToxicityVersion.conversation_id == conv_id,
            ToxicityVersion.version < latest_ver,
            ToxicityVersion.created_at < cutoff_date
        ).delete()
        deleted_count += result
    
    session.commit()
    print(f"Deleted {deleted_count} old versions")
```

### Vacuum Databases (Optimize)

```bash
# Reclaim space and optimize
sqlite3 chat_memory.db "VACUUM;"
sqlite3 toxicity_data.db "VACUUM;"

# Check database size
ls -lh *.db
```

---

## Troubleshooting

### Issue: Database Locked

**Symptom**: `database is locked` error

**Cause**: Another process is accessing the database

**Fix:**
```bash
# Check if any process is using the database
lsof chat_memory.db
lsof toxicity_data.db

# Kill the process if needed
kill -9 <PID>

# Or wait a moment and retry
```

### Issue: Database Doesn't Exist

**Symptom**: `unable to open database file`

**Cause**: Database hasn't been created yet

**Fix:**
```bash
# Run the application once to create databases
python run.py

# Or create manually
python -c "from core.database import ToxicityDB; db = ToxicityDB()"
```

### Issue: Corrupted Database

**Symptom**: `database disk image is malformed`

**Fix:**
```bash
# Try to recover
sqlite3 toxicity_data.db ".recover" | sqlite3 toxicity_data_recovered.db

# If that fails, restore from backup
cp toxicity_data_backup.db toxicity_data.db
```

### Issue: Can't Deserialize Checkpoint

**Symptom**: `pickle.UnpicklingError` when viewing chat checkpoints

**Cause**: Checkpoint was created with different Python version or incompatible state

**Fix:**
- This is normal - checkpoints use binary serialization
- Only LangGraph needs to deserialize them
- For viewing, just look at metadata or use DB Browser

### Issue: No Data for Conversation ID

**Symptom**: `get_current_version` returns None

**Cause**: Conversation hasn't saved any versions yet

**Fix:**
```python
# Check if conversation exists
db = ToxicityDB()
history = db.get_modification_history("conv-id")
if not history:
    print("No versions saved for this conversation")
else:
    print(f"Found {len(history)} versions")
```

---

## Database Maintenance

### Regular Tasks

```bash
# Weekly backup
./scripts/backup_databases.sh

# Monthly vacuum
sqlite3 chat_memory.db "VACUUM;"
sqlite3 toxicity_data.db "VACUUM;"

# Check database integrity
sqlite3 toxicity_data.db "PRAGMA integrity_check;"
```

### Monitoring

```python
# monitor_db.py
import sqlite3
import os

def get_db_stats():
    """Get database statistics"""
    
    # Chat memory stats
    chat_size = os.path.getsize("chat_memory.db") / 1024 / 1024  # MB
    conn = sqlite3.connect("chat_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM checkpoints")
    num_checkpoints = cursor.fetchone()[0]
    conn.close()
    
    # Toxicity data stats
    tox_size = os.path.getsize("toxicity_data.db") / 1024 / 1024  # MB
    conn = sqlite3.connect("toxicity_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM toxicity_versions")
    num_versions = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT conversation_id) FROM toxicity_versions")
    num_conversations = cursor.fetchone()[0]
    conn.close()
    
    print("Database Statistics:")
    print(f"  Chat Memory: {chat_size:.2f} MB ({num_checkpoints} checkpoints)")
    print(f"  Toxicity Data: {tox_size:.2f} MB ({num_versions} versions, {num_conversations} conversations)")

if __name__ == "__main__":
    get_db_stats()
```

---

## Best Practices

### ✅ DO

- **Backup regularly** - Both databases are critical
- **Use ToxicityDB API** - Don't manually insert into toxicity_versions
- **Monitor database size** - Vacuum periodically
- **Use conversation IDs** - Track related edits together
- **Write descriptive summaries** - Make history searchable

### ❌ DON'T

- **Don't manually edit chat_memory.db** - Managed by LangGraph
- **Don't delete latest versions** - Always keep current state
- **Don't share databases** - Contains conversation data
- **Don't use same thread_id across users** - Causes conflicts
- **Don't forget to backup** - No built-in backup mechanism

---

## Quick Reference

### File Locations

```
project/
├── chat_memory.db           # Chat history (LangGraph)
├── toxicity_data.db         # JSON versions (ToxicityDB)
└── core/database.py         # ToxicityDB class
```

### Key Commands

```bash
# View databases
sqlite3 chat_memory.db ".tables"
sqlite3 toxicity_data.db "SELECT * FROM toxicity_versions LIMIT 5;"

# Backup
cp *.db backups/

# Open in GUI
open -a "DB Browser for SQLite" toxicity_data.db

# Export
sqlite3 toxicity_data.db ".mode json" ".output data.json" "SELECT * FROM toxicity_versions;"
```

### Python API

```python
from core.database import ToxicityDB

db = ToxicityDB()

# Save version
db.save_version(conv_id, data, summary)

# Get current
current = db.get_current_version(conv_id)

# Get history
history = db.get_modification_history(conv_id)

# Compare
diff = db.get_diff(conv_id, from_ver, to_ver)
```

---

## Additional Resources

- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **DB Browser**: https://sqlitebrowser.org/
- **LangGraph Checkpointer**: https://langchain-ai.github.io/langgraph/concepts/persistence/
- **ToxicityDB Source**: `core/database.py`

---

## Summary

**Chat Memory Database** (`chat_memory.db`):
- ✅ Managed automatically by LangGraph
- ✅ Stores conversation checkpoints
- ✅ Read-only for users
- ✅ Binary format (BLOB)

**Toxicity Data Database** (`toxicity_data.db`):
- ✅ Managed by ToxicityDB API
- ✅ Stores JSON versions with audit trail
- ✅ Full programmatic access
- ✅ Human-readable (JSON in TEXT field)

Both databases are critical for the application's functionality and should be backed up regularly.
