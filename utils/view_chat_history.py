# view_chat_history.py
import sqlite3
import json
import pickle

def view_chat_history(conversation_id=None, db_path="chat_memory.db"):
    """
    View chat history from LangGraph checkpoint database
    
    Args:
        conversation_id: Specific conversation to view (optional)
        db_path: Path to checkpoint database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📊 Tables in database: {[t[0] for t in tables]}\n")
    
    # Check actual columns in checkpoints table
    cursor.execute("PRAGMA table_info(checkpoints)")
    columns = cursor.fetchall()
    print(f"Columns in checkpoints: {[col[1] for col in columns]}\n")
    
    # Query checkpoints (without created_at)
    if conversation_id:
        query = """
            SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, 
                   type, checkpoint, metadata
            FROM checkpoints 
            WHERE thread_id = ?
            ORDER BY checkpoint_id
        """
        cursor.execute(query, (conversation_id,))
    else:
        query = """
            SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                   type, checkpoint, metadata
            FROM checkpoints 
            ORDER BY thread_id, checkpoint_id
        """
        cursor.execute(query)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("No chat history found.")
        return
    
    print(f"📝 Found {len(rows)} checkpoint(s)\n")
    print("=" * 80)
    
    for row in rows:
        thread_id, checkpoint_ns, checkpoint_id, parent_id, type_, checkpoint_data, metadata = row
        
        print(f"\n🔹 Thread ID: {thread_id}")
        print(f"   Checkpoint NS: {checkpoint_ns}")
        print(f"   Checkpoint ID: {checkpoint_id}")
        print(f"   Parent ID: {parent_id}")
        print(f"   Type: {type_}")
        
        # Try to parse metadata
        if metadata:
            try:
                meta = json.loads(metadata) if isinstance(metadata, str) else metadata
                print(f"   Metadata: {meta}")
            except:
                print(f"   Metadata: {metadata}")
        
        print("-" * 80)
    
    # Query writes table (actual messages and state changes)
    print("\n\n💬 MESSAGES & STATE:\n")
    print("=" * 80)
    
    # Check columns in writes table
    cursor.execute("PRAGMA table_info(writes)")
    write_columns = cursor.fetchall()
    print(f"Columns in writes: {[col[1] for col in write_columns]}\n")
    
    if conversation_id:
        query = """
            SELECT thread_id, checkpoint_ns, checkpoint_id, 
                   task_id, idx, channel, type, value
            FROM writes
            WHERE thread_id = ?
            ORDER BY checkpoint_id, idx
        """
        cursor.execute(query, (conversation_id,))
    else:
        query = """
            SELECT thread_id, checkpoint_ns, checkpoint_id,
                   task_id, idx, channel, type, value
            FROM writes
            ORDER BY thread_id, checkpoint_id, idx
        """
        cursor.execute(query)
    
    writes = cursor.fetchall()
    
    if not writes:
        print("No writes found.")
    else:
        current_thread = None
        for write in writes:
            thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type_, value = write
            
            if current_thread != thread_id:
                print(f"\n{'='*80}")
                print(f"📌 CONVERSATION: {thread_id}")
                print(f"{'='*80}")
                current_thread = thread_id
            
            print(f"\n  📨 Checkpoint: {checkpoint_id}")
            print(f"     Channel: {channel}")
            print(f"     Type: {type_}")
            print(f"     Task ID: {task_id}")
            
            # Try to decode the value
            try:
                if isinstance(value, bytes):
                    decoded_value = pickle.loads(value)
                else:
                    decoded_value = value
                
                # Handle different types of values
                if channel == "messages":
                    if hasattr(decoded_value, '__iter__') and not isinstance(decoded_value, str):
                        for msg in decoded_value:
                            if hasattr(msg, 'content'):
                                print(f"     💬 Message: {msg.content}")
                            elif hasattr(msg, 'model_dump'):
                                msg_dict = msg.model_dump()
                                print(f"     💬 Message: {msg_dict.get('content', msg_dict)}")
                            else:
                                print(f"     💬 Message: {msg}")
                    else:
                        if hasattr(decoded_value, 'content'):
                            print(f"     💬 Message: {decoded_value.content}")
                        else:
                            print(f"     💬 Message: {decoded_value}")
                
                elif channel == "last_patches":
                    print(f"     🔧 Patches: {decoded_value}")
                
                elif channel == "json_data":
                    if isinstance(decoded_value, dict):
                        # Show only INCI and some key fields
                        inci = decoded_value.get('inci', 'N/A')
                        fields_with_data = [k for k, v in decoded_value.items() if v]
                        print(f"     📊 JSON Data: INCI={inci}, Modified fields: {fields_with_data}")
                    else:
                        print(f"     📊 JSON Data: {decoded_value}")
                
                else:
                    # For other channels, show a summary
                    if isinstance(decoded_value, dict):
                        print(f"     📦 Data: {list(decoded_value.keys())}")
                    elif isinstance(decoded_value, (list, tuple)):
                        print(f"     📦 Data: List with {len(decoded_value)} items")
                    else:
                        print(f"     📦 Data: {str(decoded_value)[:100]}")
                    
            except Exception as e:
                print(f"     ⚠️  Raw (binary): {len(value)} bytes")
                print(f"     ⚠️  Error decoding: {e}")
            
            print()
    
    conn.close()


def list_all_conversations(db_path="chat_memory.db"):
    """List all conversation IDs"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT thread_id, COUNT(*) as checkpoint_count
        FROM checkpoints
        GROUP BY thread_id
        ORDER BY thread_id
    """)
    
    rows = cursor.fetchall()
    
    print("🗂️  All Conversations:\n")
    for thread_id, count in rows:
        print(f"   • {thread_id} ({count} checkpoints)")
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    # List all conversations
    print("\n" + "=" * 80)
    list_all_conversations()
    print("=" * 80 + "\n")
    
    # View specific conversation if provided
    if len(sys.argv) > 1:
        conv_id = sys.argv[1]
        print(f"\n📖 Viewing conversation: {conv_id}\n")
        view_chat_history(conversation_id=conv_id)
    else:
        print("\n📖 Viewing all conversations:\n")
        view_chat_history()