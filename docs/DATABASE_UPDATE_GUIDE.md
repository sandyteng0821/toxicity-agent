# Adding patch_operations to Your Database

## Your Current Database Structure

You have a clean SQLAlchemy implementation. Here's how to add `patch_operations`.

---

## Step-by-Step Update

### Step 1: Update the Model (Add Column)

In your `database.py`, update the `ToxicityVersion` class:

```python
# database.py
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
from datetime import datetime
from typing import Optional, List, Dict  # ✨ ADD Dict
import dictdiffer

Base = declarative_base()

class ToxicityVersion(Base):
    """Store each version of toxicity JSON"""
    __tablename__ = "toxicity_versions"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100), index=True)
    version = Column(Integer)
    data = Column(Text)  # JSON string
    modification_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    patch_operations = Column(Text, nullable=True)  # ✨ NEW: Store JSON patches
```

**Changes:**
1. Added `Dict` to imports (line 7)
2. Added `patch_operations = Column(Text, nullable=True)` (last line)

---

### Step 2: Update save_version() Method

Update the `save_version` method to accept and store patches:

```python
def save_version(
    self, 
    conversation_id: str, 
    data: dict, 
    modification_summary: str,
    patch_operations: Optional[List[Dict]] = None  # ✨ NEW PARAMETER
) -> ToxicityVersion:
    """Save a new version with optional patch operations"""
    session = self.get_session()
    try:
        last_version = session.query(ToxicityVersion)\
            .filter(ToxicityVersion.conversation_id == conversation_id)\
            .order_by(ToxicityVersion.version.desc())\
            .first()
        
        next_version = (last_version.version + 1) if last_version else 1
        
        version = ToxicityVersion(
            conversation_id=conversation_id,
            version=next_version,
            data=json.dumps(data, ensure_ascii=False),  # Your existing logic
            modification_summary=modification_summary
        )
        
        # ✨ NEW: Store patches if provided
        if patch_operations:
            version.patch_operations = json.dumps(patch_operations, ensure_ascii=False)
        
        session.add(version)
        session.commit()
        session.refresh(version)
        return version
    finally:
        session.close()
```

**Changes:**
1. Added `patch_operations: Optional[List[Dict]] = None` parameter
2. Added 3 lines to store patches if provided:
   ```python
   if patch_operations:
       version.patch_operations = json.dumps(patch_operations, ensure_ascii=False)
   ```

---

### Step 3: Add Helper Method (Optional but Useful)

Add a new method to retrieve patches:

```python
def get_version_patches(self, conversation_id: str, version: Optional[int] = None) -> Optional[List[Dict]]:
    """Get patch operations for a specific version or latest"""
    session = self.get_session()
    try:
        query = session.query(ToxicityVersion)\
            .filter(ToxicityVersion.conversation_id == conversation_id)
        
        if version:
            query = query.filter(ToxicityVersion.version == version)
        else:
            query = query.order_by(ToxicityVersion.version.desc())
        
        version_obj = query.first()
        
        if version_obj and version_obj.patch_operations:
            return json.loads(version_obj.patch_operations)
        return None
    finally:
        session.close()


def get_modification_history_with_patches(self, conversation_id: str) -> List[dict]:
    """Get all modification summaries WITH patch details"""
    session = self.get_session()
    try:
        versions = session.query(ToxicityVersion)\
            .filter(ToxicityVersion.conversation_id == conversation_id)\
            .order_by(ToxicityVersion.version.asc())\
            .all()
        
        history = []
        for v in versions:
            entry = {
                "version": v.version,
                "summary": v.modification_summary,
                "timestamp": v.created_at.isoformat()
            }
            
            # ✨ NEW: Add patch details if available
            if v.patch_operations:
                patches = json.loads(v.patch_operations)
                entry["patches"] = patches
                entry["patch_count"] = len(patches)
                
                # Add human-readable patch summary
                patch_summaries = []
                for patch in patches:
                    op = patch.get('op', 'unknown')
                    path = patch.get('path', 'unknown')
                    patch_summaries.append(f"{op} at {path}")
                entry["patch_summary"] = ", ".join(patch_summaries)
            
            history.append(entry)
        
        return history
    finally:
        session.close()
```

---

### Step 4: Update Database Schema

Since you already have an existing database, you need to add the column.

#### Option A: Using Alembic (Recommended for Production)

1. **Install Alembic** (if not already):
   ```bash
   pip install alembic --break-system-packages
   ```

2. **Initialize Alembic** (if not already):
   ```bash
   alembic init alembic
   ```

3. **Configure Alembic** (`alembic.ini`):
   ```ini
   sqlalchemy.url = sqlite:///toxicity_data.db
   ```

4. **Create Migration**:
   ```bash
   alembic revision -m "add_patch_operations_column"
   ```

5. **Edit the migration file** (`alembic/versions/xxxx_add_patch_operations_column.py`):
   ```python
   def upgrade():
       op.add_column('toxicity_versions', 
                     sa.Column('patch_operations', sa.Text(), nullable=True))

   def downgrade():
       op.drop_column('toxicity_versions', 'patch_operations')
   ```

6. **Run Migration**:
   ```bash
   alembic upgrade head
   ```

#### Option B: Direct SQL (Quick for Development)

```python
# Run this ONCE to add the column to your existing database

from database import ToxicityDB
from sqlalchemy import text

db = ToxicityDB()

with db.engine.connect() as conn:
    # Check if column exists
    result = conn.execute(text("PRAGMA table_info(toxicity_versions)"))
    columns = [row[1] for row in result]
    
    if 'patch_operations' not in columns:
        # Add the column
        conn.execute(text(
            "ALTER TABLE toxicity_versions ADD COLUMN patch_operations TEXT"
        ))
        conn.commit()
        print("✅ Added patch_operations column")
    else:
        print("✅ Column already exists")
```

Save this as `migrate_db.py` and run:
```bash
python migrate_db.py
```

#### Option C: Recreate Database (ONLY if you have no important data)

```python
# WARNING: This deletes all data!

from database import Base, ToxicityDB
import os

# Delete old database
if os.path.exists("toxicity_data.db"):
    os.remove("toxicity_data.db")

# Create new database with updated schema
db = ToxicityDB()
print("✅ Database recreated with new schema")
```

---

## Complete Updated database.py

Here's your complete updated file:

```python
# database.py
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
from datetime import datetime
from typing import Optional, List, Dict
import dictdiffer

Base = declarative_base()

class ToxicityVersion(Base):
    """Store each version of toxicity JSON"""
    __tablename__ = "toxicity_versions"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100), index=True)
    version = Column(Integer)
    data = Column(Text)  # JSON string
    modification_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    patch_operations = Column(Text, nullable=True)  # ✨ NEW


class ToxicityDB:
    """Database manager for toxicity data versioning"""
    
    def __init__(self, db_path: str = "toxicity_data.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def save_version(
        self, 
        conversation_id: str, 
        data: dict, 
        modification_summary: str,
        patch_operations: Optional[List[Dict]] = None  # ✨ NEW
    ) -> ToxicityVersion:
        """Save a new version with optional patch operations"""
        session = self.get_session()
        try:
            last_version = session.query(ToxicityVersion)\
                .filter(ToxicityVersion.conversation_id == conversation_id)\
                .order_by(ToxicityVersion.version.desc())\
                .first()
            
            next_version = (last_version.version + 1) if last_version else 1
            
            version = ToxicityVersion(
                conversation_id=conversation_id,
                version=next_version,
                data=json.dumps(data, ensure_ascii=False),
                modification_summary=modification_summary
            )
            
            # ✨ NEW: Store patches if provided
            if patch_operations:
                version.patch_operations = json.dumps(patch_operations, ensure_ascii=False)
            
            session.add(version)
            session.commit()
            session.refresh(version)
            return version
        finally:
            session.close()
    
    def get_current_version(self, conversation_id: str) -> Optional[ToxicityVersion]:
        """Get latest version"""
        session = self.get_session()
        try:
            return session.query(ToxicityVersion)\
                .filter(ToxicityVersion.conversation_id == conversation_id)\
                .order_by(ToxicityVersion.version.desc())\
                .first()
        finally:
            session.close()
    
    def get_modification_history(self, conversation_id: str) -> List[dict]:
        """Get all modification summaries"""
        session = self.get_session()
        try:
            versions = session.query(ToxicityVersion)\
                .filter(ToxicityVersion.conversation_id == conversation_id)\
                .order_by(ToxicityVersion.version.asc())\
                .all()
            return [
                {
                    "version": v.version,
                    "summary": v.modification_summary,
                    "timestamp": v.created_at.isoformat()
                }
                for v in versions
            ]
        finally:
            session.close()
    
    # ✨ NEW METHODS (Optional but useful)
    
    def get_version_patches(self, conversation_id: str, version: Optional[int] = None) -> Optional[List[Dict]]:
        """Get patch operations for a specific version or latest"""
        session = self.get_session()
        try:
            query = session.query(ToxicityVersion)\
                .filter(ToxicityVersion.conversation_id == conversation_id)
            
            if version:
                query = query.filter(ToxicityVersion.version == version)
            else:
                query = query.order_by(ToxicityVersion.version.desc())
            
            version_obj = query.first()
            
            if version_obj and version_obj.patch_operations:
                return json.loads(version_obj.patch_operations)
            return None
        finally:
            session.close()
    
    def get_modification_history_with_patches(self, conversation_id: str) -> List[dict]:
        """Get all modification summaries WITH patch details"""
        session = self.get_session()
        try:
            versions = session.query(ToxicityVersion)\
                .filter(ToxicityVersion.conversation_id == conversation_id)\
                .order_by(ToxicityVersion.version.asc())\
                .all()
            
            history = []
            for v in versions:
                entry = {
                    "version": v.version,
                    "summary": v.modification_summary,
                    "timestamp": v.created_at.isoformat()
                }
                
                # Add patch details if available
                if v.patch_operations:
                    patches = json.loads(v.patch_operations)
                    entry["patches"] = patches
                    entry["patch_count"] = len(patches)
                    
                    # Add human-readable patch summary
                    patch_summaries = []
                    for patch in patches:
                        op = patch.get('op', 'unknown')
                        path = patch.get('path', 'unknown')
                        patch_summaries.append(f"{op} at {path}")
                    entry["patch_summary"] = ", ".join(patch_summaries)
                
                history.append(entry)
            
            return history
        finally:
            session.close()
```

---

## Quick Migration Script

Create `migrate_db.py` in the same directory as `database.py`:

```python
# migrate_db.py
"""
Quick migration script to add patch_operations column
Run this ONCE: python migrate_db.py
"""

from database import ToxicityDB
from sqlalchemy import text

def migrate():
    print("Starting database migration...")
    
    db = ToxicityDB()
    
    with db.engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(toxicity_versions)"))
        columns = [row[1] for row in result]
        
        if 'patch_operations' not in columns:
            print("Adding patch_operations column...")
            conn.execute(text(
                "ALTER TABLE toxicity_versions ADD COLUMN patch_operations TEXT"
            ))
            conn.commit()
            print("✅ Successfully added patch_operations column")
        else:
            print("✅ Column patch_operations already exists")
    
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
```

Run it:
```bash
python migrate_db.py
```

---

## Testing the Update

After migration, test that it works:

```python
# test_db_update.py
from database import ToxicityDB
import json

db = ToxicityDB()

# Test data
test_data = {
    "inci": "Test Chemical",
    "acute_toxicity": []
}

# Test patches
test_patches = [
    {
        "op": "add",
        "path": "/acute_toxicity/-",
        "value": {"reference": "Test", "data": "LD50=500", "source": "", "statement": "", "replaced": False}
    }
]

# Save with patches
version = db.save_version(
    conversation_id="test-001",
    data=test_data,
    modification_summary="Test save with patches",
    patch_operations=test_patches
)

print(f"✅ Saved version {version.id}")
print(f"Patch operations: {version.patch_operations}")

# Retrieve and verify
retrieved_patches = db.get_version_patches("test-001")
print(f"✅ Retrieved patches: {retrieved_patches}")

# Get history with patches
history = db.get_modification_history_with_patches("test-001")
print(f"✅ History with patches: {json.dumps(history, indent=2)}")
```

---

## Summary of Changes

**What changed:**
1. ✅ Added `patch_operations` column to `ToxicityVersion` model
2. ✅ Updated `save_version()` to accept and store patches
3. ✅ Added helper methods to retrieve patches (optional)
4. ✅ Need to run migration to add column to existing database

**Next steps:**
1. Update your `database.py` file
2. Run `migrate_db.py` to add the column
3. Test with `test_db_update.py`
4. Continue to Phase 4 of integration!

The column is `nullable=True` so existing data won't be affected.
