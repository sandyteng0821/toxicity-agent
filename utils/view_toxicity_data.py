# view_toxicity_data.py
import sqlite3
import json
from datetime import datetime

def view_toxicity_data(conversation_id=None, db_path="toxicity_data.db"):
    """
    View toxicity data from your database
    
    Args:
        conversation_id: Specific conversation to view (optional)
        db_path: Path to toxicity database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📊 Tables: {[t[0] for t in tables]}\n")
    
    # Check columns
    cursor.execute("PRAGMA table_info(toxicity_versions)")
    columns = cursor.fetchall()
    print(f"Columns: {[col[1] for col in columns]}\n")
    print("=" * 100)
    
    # Query data
    if conversation_id:
        query = """
            SELECT id, conversation_id, version, data, modification_summary, 
                   created_at, patch_operations
            FROM toxicity_versions 
            WHERE conversation_id = ?
            ORDER BY version
        """
        cursor.execute(query, (conversation_id,))
    else:
        query = """
            SELECT id, conversation_id, version, data, modification_summary,
                   created_at, patch_operations
            FROM toxicity_versions 
            ORDER BY conversation_id, version
        """
        cursor.execute(query)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ No toxicity data found.")
        return
    
    print(f"\n📝 Found {len(rows)} version(s)\n")
    
    current_conv = None
    for row in rows:
        id_, conv_id, version, data, summary, created_at, patches = row
        
        # New conversation header
        if current_conv != conv_id:
            print("\n" + "=" * 100)
            print(f"🧪 CONVERSATION: {conv_id}")
            print("=" * 100)
            current_conv = conv_id
        
        print(f"\n📌 Version {version} (ID: {id_})")
        print(f"   ⏰ Created: {created_at}")
        print(f"   📝 Summary: {summary}")
        
        # Parse and display JSON data
        try:
            json_data = json.loads(data)
            
            print(f"\n   📊 JSON Data:")
            print(f"      INCI: {json_data.get('inci', 'N/A')}")
            print(f"      CAS: {json_data.get('cas', [])}")
            print(f"      Category: {json_data.get('category', 'N/A')}")
            print(f"      Is Skip: {json_data.get('isSkip', False)}")
            
            # Show fields with data
            print(f"\n   📋 Fields with data:")
            for field in ['acute_toxicity', 'skin_irritation', 'skin_sensitization', 
                         'ocular_irritation', 'phototoxicity', 'repeated_dose_toxicity',
                         'percutaneous_absorption', 'ingredient_profile', 'NOAEL', 'DAP']:
                if field in json_data and json_data[field]:
                    count = len(json_data[field]) if isinstance(json_data[field], list) else 1
                    print(f"      • {field}: {count} entries")
            
            # Show NOAEL/DAP values if present
            if json_data.get('NOAEL'):
                print(f"\n   📈 NOAEL: {json_data['NOAEL']}")
            if json_data.get('DAP'):
                print(f"   📈 DAP: {json_data['DAP']}")
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️ Could not parse JSON: {e}")
        
        # Parse and display patches
        if patches:
            try:
                patch_list = json.loads(patches)
                print(f"\n   🔧 Patches applied ({len(patch_list)}):")
                for i, patch in enumerate(patch_list, 1):
                    op = patch.get('op', 'unknown')
                    path = patch.get('path', 'unknown')
                    value = patch.get('value', None)
                    
                    print(f"      {i}. {op.upper()} at {path}")
                    
                    # Show value preview
                    if value is not None:
                        if isinstance(value, dict):
                            keys = list(value.keys())
                            print(f"         Value: dict with keys {keys}")
                        elif isinstance(value, list):
                            print(f"         Value: list with {len(value)} items")
                        else:
                            value_str = str(value)
                            if len(value_str) > 50:
                                print(f"         Value: {value_str[:50]}...")
                            else:
                                print(f"         Value: {value_str}")
            except json.JSONDecodeError as e:
                print(f"   ⚠️ Could not parse patches: {e}")
        else:
            print(f"\n   ℹ️  No patches recorded")
        
        print("\n" + "-" * 100)
    
    conn.close()


def list_all_conversations(db_path="toxicity_data.db"):
    """List all conversation IDs with version counts"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT conversation_id, COUNT(*) as version_count, 
               MIN(created_at) as first_edit, MAX(created_at) as last_edit
        FROM toxicity_versions
        GROUP BY conversation_id
        ORDER BY last_edit DESC
    """)
    
    rows = cursor.fetchall()
    
    print("\n🗂️  All Conversations:\n")
    
    for conv_id, count, first_edit, last_edit in rows:
        print(f"📁 {conv_id}")
        print(f"   Versions: {count}")
        print(f"   First Edit: {first_edit}")
        print(f"   Last Edit: {last_edit}")
        print()
    
    conn.close()


def view_latest_by_inci(inci_name, db_path="toxicity_data.db"):
    """View latest version for a specific INCI"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, conversation_id, version, data, modification_summary, created_at
        FROM toxicity_versions
        ORDER BY id DESC
    """)
    
    for row in cursor.fetchall():
        id_, conv_id, version, data, summary, created_at = row
        try:
            json_data = json.loads(data)
            if json_data.get('inci', '').lower() == inci_name.lower():
                print(f"\n📌 Found: {inci_name}")
                print(f"   Conversation: {conv_id}")
                print(f"   Version: {version}")
                print(f"   Last Updated: {created_at}")
                print(f"   Summary: {summary}")
                print(f"\n   Full Data:")
                print(json.dumps(json_data, indent=2, ensure_ascii=False))
                conn.close()
                return
        except:
            continue
    
    print(f"❌ No data found for INCI: {inci_name}")
    conn.close()


if __name__ == "__main__":
    import sys
    
    # List all conversations
    print("\n" + "=" * 100)
    list_all_conversations()
    print("=" * 100)
    
    # View specific conversation or INCI
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # Check if it's --inci flag
        if arg == "--inci" and len(sys.argv) > 2:
            inci_name = sys.argv[2]
            print(f"\n🔍 Searching for INCI: {inci_name}\n")
            view_latest_by_inci(inci_name)
        else:
            # Treat as conversation ID
            print(f"\n📖 Viewing conversation: {arg}\n")
            view_toxicity_data(conversation_id=arg)
    else:
        print("\n📖 Viewing all data:\n")
        view_toxicity_data()