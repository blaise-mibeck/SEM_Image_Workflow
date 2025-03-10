"""
Session management module for SEM image workflows.
"""

import os
import json
import datetime
from typing import List, Dict, Any, Optional


class EditRecord:
    """Records a change to session information."""
    
    def __init__(self, user: str, field: str, old_value: Any, new_value: Any):
        self.user = user
        self.field = field
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = datetime.datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert edit record to dictionary."""
        return {
            "user": self.user,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditRecord':
        """Create edit record from dictionary."""
        record = cls(
            data.get("user"),
            data.get("field"),
            data.get("old_value"),
            data.get("new_value")
        )
        record.timestamp = data.get("timestamp")
        return record


class Session:
    """Represents a SEM imaging session for one sample."""
    
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.sample_id = None
        self.sample_type = None
        self.preparation_method = None
        self.operator_name = None
        self.notes = None
        self.creation_date = datetime.datetime.now().isoformat()
        self.last_modified = self.creation_date
        self.last_modified_by = None
        self.edit_history: List[EditRecord] = []
        self.images: List[str] = []  # List of image paths in the session
        
        # If the folder exists, scan for images
        if os.path.exists(folder_path):
            self._scan_images()
    
    def _scan_images(self) -> None:
        """Scan the session folder for images (only in the root folder, not subfolders)."""
        self.images = []
        
        # Only look at files directly in the session folder, not in subfolders
        for file in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, file)
            # Only include files (not directories) that are .tiff or .tif
            if os.path.isfile(file_path) and file.lower().endswith(('.tiff', '.tif')):
                self.images.append(file_path)
    
    def add_edit_record(self, user: str, field: str, old_value: Any, new_value: Any) -> None:
        """Track changes to session information."""
        record = EditRecord(user, field, old_value, new_value)
        self.edit_history.append(record)
        self.last_modified = record.timestamp
        self.last_modified_by = user
    
    def update_field(self, user: str, field: str, value: Any) -> None:
        """Update a session field and record the change."""
        if hasattr(self, field):
            old_value = getattr(self, field)
            setattr(self, field, value)
            self.add_edit_record(user, field, old_value, value)
        else:
            raise AttributeError(f"Session has no attribute '{field}'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization."""
        return {
            "folder_path": self.folder_path,
            "sample_id": self.sample_id,
            "sample_type": self.sample_type,
            "preparation_method": self.preparation_method,
            "operator_name": self.operator_name,
            "notes": self.notes,
            "creation_date": self.creation_date,
            "last_modified": self.last_modified,
            "last_modified_by": self.last_modified_by,
            "edit_history": [record.to_dict() for record in self.edit_history],
            "image_count": len(self.images)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], folder_path: Optional[str] = None) -> 'Session':
        """Create session from dictionary (from JSON)."""
        # Use provided folder_path or the one from the data
        path = folder_path or data.get("folder_path")
        if not path:
            raise ValueError("Folder path is required")
            
        session = cls(path)
        session.sample_id = data.get("sample_id")
        session.sample_type = data.get("sample_type")
        session.preparation_method = data.get("preparation_method")
        session.operator_name = data.get("operator_name")
        session.notes = data.get("notes")
        session.creation_date = data.get("creation_date")
        session.last_modified = data.get("last_modified")
        session.last_modified_by = data.get("last_modified_by")
        
        # Reconstruct edit history
        edit_history_data = data.get("edit_history", [])
        session.edit_history = [
            EditRecord.from_dict(record_data) for record_data in edit_history_data
        ]
        
        # Rescan images to ensure we have the latest
        session._scan_images()
        
        return session


class SessionRepository:
    """Manages persistence of session information."""
    
    SESSION_FILE_NAME = "session_info.json"
    
    def __init__(self):
        """Initialize the repository."""
        pass
    
    def session_exists(self, folder_path: str) -> bool:
        """Check if session information exists in the folder."""
        session_file_path = os.path.join(folder_path, self.SESSION_FILE_NAME)
        return os.path.exists(session_file_path)
    
    def load_session(self, folder_path: str) -> Session:
        """
        Load session from folder.
        
        Args:
            folder_path (str): Path to the session folder
            
        Returns:
            Session: Loaded session information
            
        Raises:
            FileNotFoundError: If session file doesn't exist
        """
        session_file_path = os.path.join(folder_path, self.SESSION_FILE_NAME)
        
        if not os.path.exists(session_file_path):
            raise FileNotFoundError(f"Session file not found: {session_file_path}")
        
        try:
            with open(session_file_path, 'r') as f:
                session_data = json.load(f)
            
            return Session.from_dict(session_data, folder_path)
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in session file: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Error loading session: {str(e)}")
    
    def save_session(self, session: Session) -> None:
        """
        Save session to JSON file.
        
        Args:
            session (Session): Session to save
            
        Raises:
            ValueError: If session folder path is invalid
            RuntimeError: If unable to save session file
        """
        if not session.folder_path or not os.path.exists(session.folder_path):
            raise ValueError(f"Invalid session folder path: {session.folder_path}")
        
        session_file_path = os.path.join(session.folder_path, self.SESSION_FILE_NAME)
        
        try:
            # Convert session to dictionary
            session_data = session.to_dict()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(session_file_path), exist_ok=True)
            
            # Write to file
            with open(session_file_path, 'w') as f:
                json.dump(session_data, f, indent=4)
                
        except Exception as e:
            raise RuntimeError(f"Error saving session: {str(e)}")
    
    def create_session(self, folder_path: str) -> Session:
        """
        Create a new session for the specified folder.
        
        Args:
            folder_path (str): Path to the session folder
            
        Returns:
            Session: New session object
        """
        return Session(folder_path)


# Example usage (to be removed in final version):
if __name__ == "__main__":
    # Test the session repository
    repo = SessionRepository()
    session_folder = "path/to/session/folder"
    
    # Create or load session
    if repo.session_exists(session_folder):
        session = repo.load_session(session_folder)
        print(f"Loaded existing session for sample: {session.sample_id}")
    else:
        session = repo.create_session(session_folder)
        session.update_field("test_user", "sample_id", "TEST-001")
        session.update_field("test_user", "sample_type", "Test Sample")
        repo.save_session(session)
        print(f"Created new session for sample: {session.sample_id}")
