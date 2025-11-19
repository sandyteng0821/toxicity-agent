# database.py
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
# from sqlalchemy.ext.declarative import declarative_base # deprecated
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
from datetime import datetime, timezone
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
    # created_at = Column(DateTime, default=datetime.utcnow) # deprecated 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    patch_operations = Column(Text, nullable=True) # Add patch operation

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
            patch_operations: Optional[List[Dict]] = None
            ) -> ToxicityVersion:
        """Save a new version"""
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
            # store patch operations 
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
    # ✨ NEW METHODS for patch operations (Optional but useful)
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