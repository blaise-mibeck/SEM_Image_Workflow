#!/usr/bin/env python
"""
SEM Image Workflow Manager - Launcher Script

This script serves as the entry point for the SEM Image Workflow Manager application.
It sets up the environment and launches the main application window.
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox
import logging
import argparse


def setup_environment():
    """Set up application environment and paths."""
    # Add the parent directory to the path so modules can be imported
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Create necessary directories
    app_dir = os.path.join(os.path.expanduser("~"), ".sem_image_manager")
    os.makedirs(app_dir, exist_ok=True)
    
    # Set up logging
    log_file = os.path.join(app_dir, "app.log")
    logging.basicConfig(
        filename=log_file,
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
    
    return app_dir


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='SEM Image Workflow Manager')
    parser.add_argument('--session', '-s', help='Path to session folder to open')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    
    return parser.parse_args()


def show_error_dialog(error_msg, error_details=None):
    """Display error dialog with details."""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    messagebox.showerror(
        "Error Starting Application",
        f"{error_msg}\n\n{error_details}" if error_details else error_msg
    )
    
    root.destroy()


def main():
    """Main entry point for the application."""
    try:
        # Set up environment
        app_dir = setup_environment()
        
        # Parse command line arguments
        args = parse_arguments()
        
        # Set debug level if requested
        if args.debug:
            logging.getLogger('').setLevel(logging.DEBUG)
            logging.debug("Debug mode enabled")
        
        # Import modules after environment setup
        try:
            from main import App
        except ImportError as e:
            show_error_dialog(
                "Failed to import application modules.",
                f"Error: {str(e)}\n\nPlease make sure the application is properly installed."
            )
            logging.error(f"Import error: {str(e)}")
            return 1
        
        # Create and run application
        root = tk.Tk()
        app = App(root)
        
        # Open session if specified
        if args.session and os.path.isdir(args.session):
            root.after(500, lambda: app._open_session(args.session))
        
        root.mainloop()
        
        return 0
        
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Unhandled exception: {str(e)}\n{error_details}")
        show_error_dialog(
            "An unexpected error occurred while starting the application.",
            error_details
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
