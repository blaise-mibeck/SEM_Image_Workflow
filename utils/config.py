"""
Configuration module for SEM Image Workflow Manager.

This module provides application-wide configuration settings and utilities.
"""

import os
import json
import logging
from typing import Dict, Any, Optional


# Application information
APP_NAME = "SEM Image Workflow Manager"
APP_VERSION = "1.0.0"
CONFIG_FILENAME = "config.json"
LOG_FILENAME = "app.log"

# Default configuration
DEFAULT_CONFIG = {
    "recent_sessions": [],
    "last_user": "",
    "default_workflow": "MagGrid",
    "export_path": "",
    "ui": {
        "theme": "default",
        "window_width": 1200,
        "window_height": 800
    },
    "grid_options": {
        "default_layout": "auto",
        "default_annotation_style": "solid",
        "padding": 4
    },
    "metadata": {
        "cache_enabled": True,
        "extract_on_load": False
    }
}


class Config:
    """Configuration manager class."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path (Optional[str]): Path to configuration file
        """
        # Set config path
        if config_path:
            self.config_path = config_path
        else:
            # Use user's home directory
            home_dir = os.path.expanduser("~")
            app_dir = os.path.join(home_dir, f".{APP_NAME.lower().replace(' ', '_')}")
            os.makedirs(app_dir, exist_ok=True)
            self.config_path = os.path.join(app_dir, CONFIG_FILENAME)
        
        # Set up logging
        log_path = os.path.join(os.path.dirname(self.config_path), LOG_FILENAME)
        self._setup_logging(log_path)
        
        # Load configuration
        self.config = self._load_config()
    
    def _setup_logging(self, log_path: str) -> None:
        """
        Set up logging configuration.
        
        Args:
            log_path (str): Path to log file
        """
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add console handler
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        # Start with default configuration
        config = DEFAULT_CONFIG.copy()
        
        # Try to load from file
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Update default config with loaded values
                self._update_dict_recursive(config, loaded_config)
                
                logging.info(f"Configuration loaded from {self.config_path}")
                
            except Exception as e:
                logging.error(f"Error loading configuration: {str(e)}")
        else:
            logging.info(f"No configuration file found at {self.config_path}, using defaults")
            
            # Save default configuration
            self._save_config(config)
        
        return config
    
    def _update_dict_recursive(self, target: Dict, source: Dict) -> None:
        """
        Update target dictionary with source values recursively.
        
        Args:
            target (Dict): Target dictionary to update
            source (Dict): Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively update nested dictionaries
                self._update_dict_recursive(target[key], value)
            else:
                # Update or add value
                target[key] = value
    
    def _save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            config (Optional[Dict[str, Any]]): Configuration to save
        """
        if config is None:
            config = self.config
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            logging.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logging.error(f"Error saving configuration: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key (str): Configuration key (supports dot notation for nested keys)
            default (Any): Default value if key not found
            
        Returns:
            Any: Configuration value
        """
        # Handle nested keys with dot notation
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key (str): Configuration key (supports dot notation for nested keys)
            value (Any): Value to set
        """
        # Handle nested keys with dot notation
        keys = key.split('.')
        target = self.config
        
        # Navigate to the correct nested dictionary
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            elif not isinstance(target[k], dict):
                target[k] = {}
                
            target = target[k]
        
        # Set the value
        target[keys[-1]] = value
        
        # Save configuration
        self._save_config()
    
    def add_recent_session(self, session_path: str) -> None:
        """
        Add a session to the recent sessions list.
        
        Args:
            session_path (str): Path to session folder
        """
        recent_sessions = self.get("recent_sessions", [])
        
        # Remove if already exists
        if session_path in recent_sessions:
            recent_sessions.remove(session_path)
        
        # Add to beginning of list
        recent_sessions.insert(0, session_path)
        
        # Limit to 10 recent sessions
        recent_sessions = recent_sessions[:10]
        
        # Update and save
        self.set("recent_sessions", recent_sessions)
    
    def clear_recent_sessions(self) -> None:
        """Clear the list of recent sessions."""
        self.set("recent_sessions", [])
    
    def save(self) -> None:
        """Save current configuration to file."""
        self._save_config()


# Singleton instance
_config_instance = None

def get_config() -> Config:
    """
    Get the singleton configuration instance.
    
    Returns:
        Config: Configuration manager instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# Example usage
if __name__ == "__main__":
    config = get_config()
    print(f"Default workflow: {config.get('default_workflow')}")
    print(f"Recent sessions: {config.get('recent_sessions')}")
    
    # Set a value
    config.set("ui.theme", "dark")
    print(f"Theme: {config.get('ui.theme')}")
    
    # Add a recent session
    config.add_recent_session("/path/to/session")
    print(f"Recent sessions: {config.get('recent_sessions')}")
