"""
SEM Image Workflow Manager - Main Application

This module provides the entry point for the SEM Image Workflow Manager application.
It sets up the main window and initializes the application components.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import json
import datetime

# Import application components
from models.session import Session, SessionRepository
from controllers.workflow_controllers import WorkflowFactory
from controllers.metadata_controller import MetadataExtractor
# Import the enhanced controller
from controllers.enhanced_maggrid_controller import EnhancedMagGridController

# Configuration and constants
APP_TITLE = "SEM Image Workflow Manager"
APP_VERSION = "1.0.0"
CONFIG_FILE = "config.json"


class App:
    """Main application class."""
    
    def __init__(self, root):
        """
        Initialize the application.
        
        Args:
            root (tk.Tk): Root Tkinter widget
        """
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1200x800")
        
        # Initialize session components
        self.session_repo = SessionRepository()
        self.session = None
        self.current_user = None
        self.current_workflow = None
        
        # Initialize UI components
        self._create_menu()
        self._create_main_frame()
        
        # Load configuration
        self._load_config()
        
        # Prompt for user name at startup
        self._prompt_user_login()
    
    def _load_config(self):
        """Load application configuration."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "recent_sessions": [],
                    "last_user": "",
                    "default_workflow": "MagGrid"
                }
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
            self.config = {
                "recent_sessions": [],
                "last_user": "",
                "default_workflow": "MagGrid"
            }
    
    def _save_config(self):
        """Save application configuration."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def _prompt_user_login(self):
        """Prompt for user name at startup."""
        login_window = tk.Toplevel(self.root)
        login_window.title("User Login")
        login_window.geometry("300x150")
        login_window.transient(self.root)
        login_window.grab_set()
        
        # Center the login window
        login_window.update_idletasks()
        width = login_window.winfo_width()
        height = login_window.winfo_height()
        x = (login_window.winfo_screenwidth() // 2) - (width // 2)
        y = (login_window.winfo_screenheight() // 2) - (height // 2)
        login_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add login form
        frame = ttk.Frame(login_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Enter your name:").pack(pady=(0, 10))
        
        name_var = tk.StringVar(value=self.config.get("last_user", ""))
        name_entry = ttk.Entry(frame, textvariable=name_var, width=30)
        name_entry.pack(pady=(0, 20))
        name_entry.focus_set()
        
        def login():
            name = name_var.get().strip()
            if name:
                self.current_user = name
                self.config["last_user"] = name
                self._save_config()
                login_window.destroy()
                
                # If this is a fresh start, prompt to open a session
                if not self.session:
                    self._prompt_session_selection()
            else:
                messagebox.showerror("Error", "Please enter your name")
        
        ttk.Button(frame, text="Login", command=login).pack()
        
        # Bind Enter key to login button
        login_window.bind("<Return>", lambda event: login())
    
    def _create_menu(self):
        """Create application menu."""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Session", command=self._prompt_session_selection)
        file_menu.add_command(label="New Session", command=self._create_new_session)
        file_menu.add_separator()
        
        # Add recent sessions submenu
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Sessions", menu=self.recent_menu)
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Workflow menu
        workflow_menu = tk.Menu(menubar, tearoff=0)
        workflow_menu.add_command(label="MagGrid", command=lambda: self._switch_workflow("MagGrid"))
        workflow_menu.add_command(label="Enhanced MagGrid", command=lambda: self._switch_workflow("EnhancedMagGrid"))
        workflow_menu.add_command(label="ModeGrid", command=lambda: self._switch_workflow("ModeGrid"))
        workflow_menu.add_command(label="CompareGrid", command=lambda: self._switch_workflow("CompareGrid"))
        workflow_menu.add_command(label="MakeGrid", command=lambda: self._switch_workflow("MakeGrid"))
        menubar.add_cascade(label="Workflow", menu=workflow_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def _create_main_frame(self):
        """Create main application frame."""
        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create session info frame
        self.session_frame = ttk.LabelFrame(self.main_frame, text="Session Information")
        self.session_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Session info not available initially
        ttk.Label(self.session_frame, text="No session loaded").pack(pady=10)
        
        # Create workflow frame
        self.workflow_frame = ttk.LabelFrame(self.main_frame, text="Workflow")
        self.workflow_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Workflow not loaded initially
        ttk.Label(self.workflow_frame, text="No workflow selected").pack(pady=10)
        
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _update_recent_sessions_menu(self):
        """Update the recent sessions menu."""
        # Clear the menu
        self.recent_menu.delete(0, tk.END)
        
        # Add recent sessions
        for session_path in self.config.get("recent_sessions", []):
            if os.path.exists(session_path):
                session_name = os.path.basename(session_path)
                self.recent_menu.add_command(
                    label=session_name,
                    command=lambda path=session_path: self._open_session(path)
                )
        
        # Add clear option if there are recent sessions
        if self.config.get("recent_sessions"):
            self.recent_menu.add_separator()
            self.recent_menu.add_command(label="Clear Recent", command=self._clear_recent_sessions)
    
    def _clear_recent_sessions(self):
        """Clear the list of recent sessions."""
        self.config["recent_sessions"] = []
        self._save_config()
        self._update_recent_sessions_menu()
    
    def _add_to_recent_sessions(self, session_path):
        """Add a session to the recent sessions list."""
        # Remove if already exists
        if session_path in self.config.get("recent_sessions", []):
            self.config["recent_sessions"].remove(session_path)
        
        # Add to beginning of list
        self.config.setdefault("recent_sessions", []).insert(0, session_path)
        
        # Limit to 10 recent sessions
        self.config["recent_sessions"] = self.config["recent_sessions"][:10]
        
        # Save config and update menu
        self._save_config()
        self._update_recent_sessions_menu()
    
    def _prompt_session_selection(self):
        """Prompt user to select a session folder."""
        folder_path = filedialog.askdirectory(
            title="Select Session Folder",
            initialdir=os.path.dirname(self.config.get("recent_sessions", [""])[0]) if self.config.get("recent_sessions") else None
        )
        
        if folder_path:
            self._open_session(folder_path)
    
    def _create_new_session(self):
        """Create a new session."""
        folder_path = filedialog.askdirectory(
            title="Select Folder for New Session",
            initialdir=os.path.dirname(self.config.get("recent_sessions", [""])[0]) if self.config.get("recent_sessions") else None
        )
        
        if folder_path:
            # Check if session already exists
            if self.session_repo.session_exists(folder_path):
                response = messagebox.askyesno(
                    "Session Exists",
                    "A session already exists in this folder. Do you want to open it instead?"
                )
                if response:
                    self._open_session(folder_path)
                return
            
            # Create new session
            self.session = self.session_repo.create_session(folder_path)
            
            # Prompt for session information
            self._edit_session_info()
            
            # Save session
            self.session_repo.save_session(self.session)
            
            # Add to recent sessions
            self._add_to_recent_sessions(folder_path)
            
            # Update UI
            self._update_session_display()
            
            # Switch to default workflow
            self._switch_workflow(self.config.get("default_workflow", "MagGrid"))
    
    def _open_session(self, folder_path):
        """Open an existing session."""
        try:
            # Check if session exists
            if not self.session_repo.session_exists(folder_path):
                response = messagebox.askyesno(
                    "Session Not Found",
                    "No session information found in this folder. Do you want to create a new session?"
                )
                if response:
                    self.session = self.session_repo.create_session(folder_path)
                    self._edit_session_info()
                    self.session_repo.save_session(self.session)
                else:
                    return
            else:
                # Load existing session
                self.session = self.session_repo.load_session(folder_path)
            
            # Add to recent sessions
            self._add_to_recent_sessions(folder_path)
            
            # Update UI
            self._update_session_display()
            
            # Switch to default workflow
            self._switch_workflow(self.config.get("default_workflow", "MagGrid"))
            
            self.status_var.set(f"Loaded session: {os.path.basename(folder_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open session: {str(e)}")
    
    def _edit_session_info(self):
        """Edit session information."""
        if not self.session:
            messagebox.showerror("Error", "No session loaded")
            return
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Session Information")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create form
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Sample ID
        ttk.Label(frame, text="Sample ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        sample_id_var = tk.StringVar(value=self.session.sample_id or "")
        ttk.Entry(frame, textvariable=sample_id_var, width=30).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Sample Type
        ttk.Label(frame, text="Sample Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        sample_type_var = tk.StringVar(value=self.session.sample_type or "")
        ttk.Entry(frame, textvariable=sample_type_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Preparation Method
        ttk.Label(frame, text="Preparation Method:").grid(row=2, column=0, sticky=tk.W, pady=5)
        prep_method_var = tk.StringVar(value=self.session.preparation_method or "")
        ttk.Entry(frame, textvariable=prep_method_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Operator Name
        ttk.Label(frame, text="Operator Name:").grid(row=3, column=0, sticky=tk.W, pady=5)
        operator_var = tk.StringVar(value=self.session.operator_name or "")
        ttk.Entry(frame, textvariable=operator_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Notes
        ttk.Label(frame, text="Notes:").grid(row=4, column=0, sticky=tk.W, pady=5)
        notes_text = tk.Text(frame, width=30, height=6)
        notes_text.grid(row=4, column=1, sticky=tk.W, pady=5)
        if self.session.notes:
            notes_text.insert("1.0", self.session.notes)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        def save_info():
            # Update session with new values
            self.session.update_field(self.current_user, "sample_id", sample_id_var.get())
            self.session.update_field(self.current_user, "sample_type", sample_type_var.get())
            self.session.update_field(self.current_user, "preparation_method", prep_method_var.get())
            self.session.update_field(self.current_user, "operator_name", operator_var.get())
            self.session.update_field(self.current_user, "notes", notes_text.get("1.0", tk.END).strip())
            
            # Save session
            self.session_repo.save_session(self.session)
            
            # Update UI
            self._update_session_display()
            
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Save", command=save_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _update_session_display(self):
        """Update session information display."""
        # Clear existing widgets
        for widget in self.session_frame.winfo_children():
            widget.destroy()
        
        if not self.session:
            ttk.Label(self.session_frame, text="No session loaded").pack(pady=10)
            return
        
        # Create grid layout
        frame = ttk.Frame(self.session_frame, padding=10)
        frame.pack(fill=tk.X)
        
        # Session folder
        ttk.Label(frame, text="Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text=self.session.folder_path).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Sample ID
        ttk.Label(frame, text="Sample ID:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text=self.session.sample_id or "").grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Sample Type
        ttk.Label(frame, text="Sample Type:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text=self.session.sample_type or "").grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Preparation Method
        ttk.Label(frame, text="Preparation:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text=self.session.preparation_method or "").grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Operator Name
        ttk.Label(frame, text="Operator:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text=self.session.operator_name or "").grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Image count
        ttk.Label(frame, text="Images:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(frame, text=str(len(self.session.images))).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Last modified
        ttk.Label(frame, text="Last Modified:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        last_modified = self.session.last_modified or self.session.creation_date or ""
        ttk.Label(frame, text=last_modified).grid(row=3, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Edit button
        ttk.Button(frame, text="Edit", command=self._edit_session_info).grid(row=0, column=3, sticky=tk.E, padx=5, pady=2)
    
    def _switch_workflow(self, workflow_type):
        """
        Switch to a different workflow.
        
        Args:
            workflow_type (str): Type of workflow to switch to
        """
        if not self.session:
            messagebox.showerror("Error", "Please open a session first")
            return
        
        # Set as default workflow
        self.config["default_workflow"] = workflow_type
        self._save_config()
        
        # Create workflow controller
        self.current_workflow = WorkflowFactory.create_workflow(workflow_type, self.session)
        
        # Load collections
        self.current_workflow.load_collections()
        
        # Update UI
        self._update_workflow_display()
        
        self.status_var.set(f"Switched to {workflow_type} workflow")
    
    def _update_workflow_display(self):
        """Update workflow display."""
        # Clear existing widgets
        for widget in self.workflow_frame.winfo_children():
            widget.destroy()
        
        if not self.current_workflow:
            ttk.Label(self.workflow_frame, text="No workflow selected").pack(pady=10)
            return
        
        # Create main workflow frame
        frame = ttk.Frame(self.workflow_frame, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Create collections list frame
        collections_frame = ttk.LabelFrame(frame, text="Collections")
        collections_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create collections listbox
        collections_listbox = tk.Listbox(collections_frame, width=30, height=15)
        collections_listbox.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(collections_frame, orient=tk.VERTICAL, command=collections_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        collections_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate collections listbox
        for i, collection in enumerate(self.current_workflow.collections):
            collections_listbox.insert(tk.END, collection.name)
            # Select first collection by default
            if i == 0:
                collections_listbox.selection_set(i)
        
        # Create collection buttons frame
        collection_buttons_frame = ttk.Frame(collections_frame)
        collection_buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Collection buttons
        ttk.Button(collection_buttons_frame, text="New", 
                  command=self._create_new_collection).pack(side=tk.LEFT, padx=2)
        ttk.Button(collection_buttons_frame, text="Delete", 
                  command=lambda: self._delete_collection(collections_listbox)).pack(side=tk.LEFT, padx=2)
        ttk.Button(collection_buttons_frame, text="Build", 
                  command=self._build_collections).pack(side=tk.LEFT, padx=2)
        
        # Create collection details frame
        details_frame = ttk.LabelFrame(frame, text="Collection Details")
        details_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Placeholder for collection details
        ttk.Label(details_frame, text="Select a collection to view details").pack(pady=10)
        
        # Create preview frame
        preview_frame = ttk.LabelFrame(frame, text="Preview")
        preview_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Placeholder for preview
        ttk.Label(preview_frame, text="Select a collection to preview").pack(pady=10)
        
        # Export button
        ttk.Button(preview_frame, text="Export Grid", 
                  command=lambda: self._export_grid(collections_listbox)).pack(side=tk.BOTTOM, pady=5)
        
        # Bind collection selection
        def on_collection_select(event):
            selection = collections_listbox.curselection()
            if selection:
                index = selection[0]
                collection = self.current_workflow.collections[index]
                self.current_workflow.current_collection = collection
                self._update_collection_details(details_frame, collection)
                self._update_preview(preview_frame, collection)
        
        collections_listbox.bind('<<ListboxSelect>>', on_collection_select)
        
        # If there are collections, select the first one
        if self.current_workflow.collections:
            self._update_collection_details(details_frame, self.current_workflow.collections[0])
            self._update_preview(preview_frame, self.current_workflow.collections[0])
            self.current_workflow.current_collection = self.current_workflow.collections[0]
    
    def _create_new_collection(self):
        """Create a new collection."""
        if not self.current_workflow:
            return
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("New Collection")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create form
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Collection name
        ttk.Label(frame, text="Collection Name:").pack(anchor=tk.W)
        name_var = tk.StringVar(value=f"{self.current_workflow.get_workflow_type()}_{len(self.current_workflow.collections) + 1}")
        ttk.Entry(frame, textvariable=name_var, width=30).pack(pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        def create_collection():
            name = name_var.get().strip()
            if name:
                collection = self.current_workflow.create_collection(name)
                collection.created_by = self.current_user
                self.current_workflow.save_collections()
                self._update_workflow_display()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Please enter a collection name")
        
        ttk.Button(btn_frame, text="Create", command=create_collection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _delete_collection(self, listbox):
        """
        Delete the selected collection.
        
        Args:
            listbox (tk.Listbox): Listbox containing collections
        """
        if not self.current_workflow:
            return
            
        selection = listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a collection to delete")
            return
            
        index = selection[0]
        collection = self.current_workflow.collections[index]
        
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the collection '{collection.name}'?"
        )
        
        if response:
            self.current_workflow.delete_collection(collection)
            self.current_workflow.save_collections()
            self._update_workflow_display()
    
    def _build_collections(self):
        """Build collections based on workflow criteria."""
        if not self.current_workflow:
            return
            
        response = messagebox.askyesno(
            "Build Collections",
            f"This will automatically build collections for the {self.current_workflow.get_workflow_type()} workflow. Proceed?"
        )
        
        if response:
            try:
                # Show progress indicator
                self.status_var.set("Building collections...")
                self.root.update_idletasks()
                
                # Build collections
                new_collections = self.current_workflow.build_collections()
                
                # Add created_by information
                for collection in new_collections:
                    collection.created_by = self.current_user
                
                # Add to existing collections
                self.current_workflow.collections.extend(new_collections)
                
                # Save collections
                self.current_workflow.save_collections()
                
                # Update UI
                self._update_workflow_display()
                
                messagebox.showinfo(
                    "Build Complete",
                    f"Built {len(new_collections)} new collections"
                )
                
                self.status_var.set("Ready")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to build collections: {str(e)}")
                self.status_var.set("Ready")
    
    def _update_collection_details(self, frame, collection):
        """
        Update collection details display.
        
        Args:
            frame (ttk.Frame): Frame to update
            collection (Collection): Collection to display
        """
        # Clear existing widgets
        for widget in frame.winfo_children():
            widget.destroy()
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add collection details
        ttk.Label(scrollable_frame, text=f"Name: {collection.name}").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(scrollable_frame, text=f"Type: {collection.workflow_type}").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(scrollable_frame, text=f"Created by: {collection.created_by or 'Unknown'}").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(scrollable_frame, text=f"Creation date: {collection.creation_date}").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Label(scrollable_frame, text=f"Images: {len(collection.images)}").pack(anchor=tk.W, padx=10, pady=2)
        
        # Add workflow-specific details
        if collection.workflow_type == "MagGrid" or collection.workflow_type == "EnhancedMagGrid":
            ttk.Label(scrollable_frame, text=f"Magnification Levels: {len(collection.magnification_levels)}").pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(scrollable_frame, text="Magnifications:").pack(anchor=tk.W, padx=10, pady=2)
            for mag in sorted(collection.magnification_levels.keys()):
                ttk.Label(scrollable_frame, text=f"- {mag}x: {len(collection.magnification_levels[mag])} images").pack(anchor=tk.W, padx=20, pady=1)
        
        elif collection.workflow_type == "ModeGrid":
            ttk.Label(scrollable_frame, text=f"Modes: {len(collection.mode_map)}").pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(scrollable_frame, text="Available modes:").pack(anchor=tk.W, padx=10, pady=2)
            for mode in collection.mode_map:
                ttk.Label(scrollable_frame, text=f"- {mode}: {len(collection.mode_map[mode])} images").pack(anchor=tk.W, padx=20, pady=1)
            ttk.Label(scrollable_frame, text=f"Magnification: {collection.magnification}x").pack(anchor=tk.W, padx=10, pady=2)
        
        elif collection.workflow_type == "CompareGrid":
            ttk.Label(scrollable_frame, text=f"Samples: {len(collection.sample_images)}").pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(scrollable_frame, text="Sample IDs:").pack(anchor=tk.W, padx=10, pady=2)
            for sample_id in collection.sample_images:
                ttk.Label(scrollable_frame, text=f"- {sample_id}").pack(anchor=tk.W, padx=20, pady=1)
            ttk.Label(scrollable_frame, text=f"Mode: {collection.mode}").pack(anchor=tk.W, padx=10, pady=2)
            ttk.Label(scrollable_frame, text=f"Magnification: {collection.magnification}x").pack(anchor=tk.W, padx=10, pady=2)
        
        # Add images section
        ttk.Label(scrollable_frame, text="Images:").pack(anchor=tk.W, padx=10, pady=5)
        for i, image_path in enumerate(collection.images[:10]):  # Limit to first 10
            ttk.Label(scrollable_frame, text=f"- {os.path.basename(image_path)}").pack(anchor=tk.W, padx=20, pady=1)
        
        if len(collection.images) > 10:
            ttk.Label(scrollable_frame, text=f"... and {len(collection.images) - 10} more").pack(anchor=tk.W, padx=20, pady=1)
    
    def _update_preview(self, frame, collection):
        """
        Update preview display.
        
        Args:
            frame (ttk.Frame): Frame to update
            collection (Collection): Collection to preview
        """
        # Clear existing widgets
        for widget in frame.winfo_children():
            widget.destroy()
        
        try:
            # Create grid visualization
            grid_img = self.current_workflow.create_grid_visualization(collection)
            
            # Resize for preview (maintain aspect ratio)
            max_width = 400
            max_height = 300
            
            width, height = grid_img.size
            ratio = min(max_width / width, max_height / height)
            new_size = (int(width * ratio), int(height * ratio))
            
            resized_img = grid_img.resize(new_size, Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(resized_img)
            
            # Add to frame
            img_label = ttk.Label(frame, image=photo)
            img_label.image = photo  # Keep a reference to prevent garbage collection
            img_label.pack(pady=5)
            
            # Add export button
            ttk.Button(frame, text="Export Grid", 
                      command=lambda: self._export_grid_for_collection(collection)).pack(pady=5)
            
        except Exception as e:
            ttk.Label(frame, text=f"Error generating preview: {str(e)}").pack(pady=10)
    
    def _export_grid(self, listbox):
        """
        Export grid for the selected collection.
        
        Args:
            listbox (tk.Listbox): Listbox containing collections
        """
        if not self.current_workflow:
            return
            
        selection = listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a collection to export")
            return
            
        index = selection[0]
        collection = self.current_workflow.collections[index]
        
        self._export_grid_for_collection(collection)
    
    def _export_grid_for_collection(self, collection):
        """
        Export grid for a specific collection.
        
        Args:
            collection (Collection): Collection to export
        """
        try:
            # Create export options dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Export Grid")
            dialog.geometry("400x250")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Center the dialog
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # Create form
            frame = ttk.Frame(dialog, padding=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Grid layout
            ttk.Label(frame, text="Grid Layout:").grid(row=0, column=0, sticky=tk.W, pady=5)
            
            layout_var = tk.StringVar(value="auto")
            ttk.Radiobutton(frame, text="Auto", variable=layout_var, value="auto").grid(row=0, column=1, sticky=tk.W, pady=5)
            ttk.Radiobutton(frame, text="2×1", variable=layout_var, value="2x1").grid(row=1, column=1, sticky=tk.W, pady=5)
            ttk.Radiobutton(frame, text="2×2", variable=layout_var, value="2x2").grid(row=2, column=1, sticky=tk.W, pady=5)
            ttk.Radiobutton(frame, text="3×2", variable=layout_var, value="3x2").grid(row=3, column=1, sticky=tk.W, pady=5)
            
            # Annotation style (for MagGrid)
            ttk.Label(frame, text="Annotation Style:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=10)
            
            annotation_var = tk.StringVar(value="solid")
            ttk.Radiobutton(frame, text="Solid", variable=annotation_var, value="solid").grid(row=0, column=3, sticky=tk.W, pady=5)
            ttk.Radiobutton(frame, text="Dotted", variable=annotation_var, value="dotted").grid(row=1, column=3, sticky=tk.W, pady=5)
            ttk.Radiobutton(frame, text="None", variable=annotation_var, value="none").grid(row=2, column=3, sticky=tk.W, pady=5)
            
            # Add Template Match option for EnhancedMagGrid
            if collection.workflow_type == "EnhancedMagGrid":
                ttk.Radiobutton(frame, text="Template Match", variable=annotation_var, value="template").grid(row=3, column=3, sticky=tk.W, pady=5)
            
            # Output path
            ttk.Label(frame, text="Output Path:").grid(row=4, column=0, sticky=tk.W, pady=5)
            
            path_var = tk.StringVar(value="")
            path_entry = ttk.Entry(frame, textvariable=path_var, width=30)
            path_entry.grid(row=4, column=1, columnspan=2, sticky=tk.W+tk.E, pady=5)
            
            def browse_output():
                # Generate default filename
                session_id = os.path.basename(self.session.folder_path)
                sample_id = self.session.sample_id or "unknown"
                default_filename = f"{session_id}_{sample_id}_{collection.workflow_type}.png"
                
                filepath = filedialog.asksaveasfilename(
                    title="Save Grid Image",
                    initialfile=default_filename,
                    defaultextension=".png",
                    filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")]
                )
                
                if filepath:
                    path_var.set(filepath)
            
            ttk.Button(frame, text="Browse...", command=browse_output).grid(row=4, column=3, sticky=tk.W, pady=5)
            
            # Buttons
            btn_frame = ttk.Frame(frame)
            btn_frame.grid(row=5, column=0, columnspan=4, pady=20)
            
            def export():
                try:
                    # Determine layout
                    layout_str = layout_var.get()
                    if layout_str == "auto":
                        layout = None  # Let the controller decide
                    else:
                        rows, cols = map(int, layout_str.split("x"))
                        layout = (rows, cols)
                    
                    # Get annotation style
                    annotation_style = annotation_var.get()
                    
                    # Get output path
                    output_path = path_var.get()
                    
                    # Show progress indicator
                    self.status_var.set("Exporting grid...")
                    self.root.update_idletasks()
                    
                    # Export grid
                    if output_path:
                        result_path = self.current_workflow.export_grid(
                            collection, output_path, layout, annotation_style
                        )
                    else:
                        result_path = self.current_workflow.export_grid(
                            collection, None, layout, annotation_style
                        )
                    
                    messagebox.showinfo(
                        "Export Complete",
                        f"Grid exported to:\n{result_path}"
                    )
                    
                    self.status_var.set("Ready")
                    dialog.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export grid: {str(e)}")
                    self.status_var.set("Ready")
            
            ttk.Button(btn_frame, text="Export", command=export).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to prepare export: {str(e)}")
    
    def _show_about(self):
        """Show about dialog."""
        about_text = f"""
        {APP_TITLE} v{APP_VERSION}
        
        A tool for organizing and visualizing SEM images.
        
        Features:
        - Manage SEM session information
        - Extract and utilize image metadata
        - Create grid visualizations with different workflows
        - Export grids for reports
        
        Created for research and reporting purposes.
        """
        
        messagebox.showinfo("About", about_text.strip())


def main():
    """Main entry point."""
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()