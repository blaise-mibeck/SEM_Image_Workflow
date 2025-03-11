"""
Template Matching Plugin for SEM Image Workflow Manager.
Integrates the template matching functionality with the existing application.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
from datetime import datetime
from PIL import Image, ImageTk

# Import from main application
from controllers.workflow_controllers import MagGridController
from enhanced_maggrid_controller import EnhancedMagGridController
from template_matching import TemplateMatchingHelper


class TemplateMatchingPlugin:
    """Plugin for adding template matching capabilities to SEM Image Workflow Manager."""
    
    def __init__(self, app):
        """
        Initialize the plugin.
        
        Args:
            app: The main application instance
        """
        self.app = app
        self.template_matcher = TemplateMatchingHelper()
        
        # Add menu options
        self._add_menu_options()
        
        # Create plugin dialog
        self.dialog = None
        
        # State variables
        self.processing_thread = None
        self.stop_processing = False
        
    def _add_menu_options(self):
        """Add plugin menu options to the main application."""
        # Check if a Tools menu exists
        tools_menu = None
        for menu in self.app.root.winfo_children():
            if isinstance(menu, tk.Menu):
                for i in range(menu.index("end") + 1):
                    try:
                        label = menu.entrycget(i, "label")
                        if label == "Tools":
                            tools_menu = menu.nametowidget(menu.entrycget(i, "menu"))
                            break
                    except:
                        pass
        
        # If no Tools menu, create one
        if not tools_menu:
            menubar = self.app.root.children["!menu"]
            tools_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Add plugin menu items
        tools_menu.add_command(label="Template Matching...", command=self.show_dialog)
        tools_menu.add_command(label="Use Enhanced MagGrid", command=self.use_enhanced_maggrid)
        
    def show_dialog(self):
        """Show the template matching dialog."""
        if self.dialog:
            self.dialog.destroy()
        
        # Create the dialog
        self.dialog = tk.Toplevel(self.app.root)
        self.dialog.title("SEM Template Matching")
        self.dialog.geometry("800x600")
        self.dialog.transient(self.app.root)
        
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Options panel
        options_frame = ttk.LabelFrame(main_frame, text="Template Matching Options")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Method selection
        method_frame = ttk.Frame(options_frame)
        method_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(method_frame, text="Matching Method:").pack(side=tk.LEFT, padx=5)
        self.method_var = tk.StringVar(value="cv2.TM_CCOEFF_NORMED")
        methods = list(self.template_matcher.methods.keys())
        method_combo = ttk.Combobox(method_frame, textvariable=self.method_var, values=methods, width=20)
        method_combo.pack(side=tk.LEFT, padx=5)
        
        # Threshold
        threshold_frame = ttk.Frame(options_frame)
        threshold_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(threshold_frame, text="Threshold:").pack(side=tk.LEFT, padx=5)
        self.threshold_var = tk.DoubleVar(value=0.5)
        threshold_slider = ttk.Scale(threshold_frame, from_=0.1, to=0.9, variable=self.threshold_var, 
                                    orient=tk.HORIZONTAL, length=300)
        threshold_slider.pack(side=tk.LEFT, padx=5)
        threshold_label = ttk.Label(threshold_frame, textvariable=self.threshold_var, width=4)
        threshold_label.pack(side=tk.LEFT, padx=5)
        
        # Options
        options_grid = ttk.Frame(options_frame)
        options_grid.pack(fill=tk.X, padx=5, pady=5)
        
        # Multi-scale option
        self.multi_scale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_grid, text="Use Multi-Scale Matching", variable=self.multi_scale_var).grid(
            row=0, column=0, sticky=tk.W, padx=5)
        
        # Use with MagGrid workflow option
        self.maggrid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_grid, text="Use with MagGrid Workflow", variable=self.maggrid_var).grid(
            row=0, column=1, sticky=tk.W, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(options_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="Run Template Matching", command=self.run_template_matching).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop", command=self.stop_processing_cmd).pack(
            side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(
            side=tk.RIGHT, padx=5)
        
        # Results panel
        results_frame = ttk.LabelFrame(main_frame, text="Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a text widget for displaying results
        self.results_text = tk.Text(results_frame, wrap=tk.WORD)
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.config(yscrollcommand=scrollbar.set)
        
        # Progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, orient=tk.HORIZONTAL, 
                                           mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Show initial status
        self._show_status()
    
    def _show_status(self):
        """Show status information in the results text widget."""
        self.results_text.delete('1.0', tk.END)
        
        if hasattr(self.app, 'session') and self.app.session:
            session_path = self.app.session.folder_path
            image_count = len(self.app.session.images)
            
            self.results_text.insert(tk.END, f"Current Session: {os.path.basename(session_path)}\n")
            self.results_text.insert(tk.END, f"Images in Session: {image_count}\n\n")
            
            if hasattr(self.app, 'current_workflow') and self.app.current_workflow:
                workflow_type = self.app.current_workflow.get_workflow_type()
                collection_count = len(self.app.current_workflow.collections)
                
                self.results_text.insert(tk.END, f"Current Workflow: {workflow_type}\n")
                self.results_text.insert(tk.END, f"Collections: {collection_count}\n\n")
                
                if workflow_type == "MagGrid":
                    self.results_text.insert(tk.END, "Template matching can enhance MagGrid collections by:\n")
                    self.results_text.insert(tk.END, "- Visually verifying containment relationships\n")
                    self.results_text.insert(tk.END, "- Finding relationships that metadata might miss\n")
                    self.results_text.insert(tk.END, "- Providing accurate bounding box visualizations\n\n")
                    
                    self.results_text.insert(tk.END, "Click 'Run Template Matching' to process this session's images.\n")
                else:
                    self.results_text.insert(tk.END, "Note: Template matching works best with MagGrid workflow.\n")
                    self.results_text.insert(tk.END, "Switch to MagGrid workflow for best results.\n")
            else:
                self.results_text.insert(tk.END, "No workflow selected. Please select a workflow first.\n")
        else:
            self.results_text.insert(tk.END, "No session loaded. Please open a session first.\n")
    
    def use_enhanced_maggrid(self):
        """Switch to using the enhanced MagGrid controller."""
        if hasattr(self.app, 'session') and self.app.session:
            # Check if current workflow is MagGrid
            if (hasattr(self.app, 'current_workflow') and self.app.current_workflow and 
                self.app.current_workflow.get_workflow_type() == "MagGrid"):
                
                # Create a new EnhancedMagGridController
                enhanced_controller = EnhancedMagGridController(self.app.session)
                
                # Load collections from the existing controller
                enhanced_controller.collections = self.app.current_workflow.collections
                enhanced_controller.current_collection = self.app.current_workflow.current_collection
                
                # Replace the current workflow controller
                self.app.current_workflow = enhanced_controller
                
                # Update UI
                if hasattr(self.app, '_update_workflow_display'):
                    self.app._update_workflow_display()
                
                messagebox.showinfo("Template Matching Plugin", 
                                  "Switched to Enhanced MagGrid controller with template matching support.")
            else:
                messagebox.showinfo("Template Matching Plugin", 
                                  "Please switch to MagGrid workflow first.")
        else:
            messagebox.showinfo("Template Matching Plugin", 
                              "Please open a session first.")
    
    def run_template_matching(self):
        """Run template matching on the current session."""
        # Check if a session is loaded
        if not hasattr(self.app, 'session') or not self.app.session:
            messagebox.showerror("Error", "Please open a session first")
            return
        
        # Get session folder and images
        session_folder = self.app.session.folder_path
        images = []
        
        # Collect images with metadata
        for image_path in self.app.session.images:
            # Create metadata object
            metadata = None
            
            # Check if the workflow controller has metadata for this image
            if (hasattr(self.app, 'current_workflow') and 
                hasattr(self.app.current_workflow, 'get_metadata')):
                metadata = self.app.current_workflow.get_metadata(image_path)
            
            # If no metadata from workflow, try to extract it directly
            if not metadata:
                from sem_metadata import SEMMetadata
                metadata = SEMMetadata(image_path)
                metadata.extract_from_tiff()
            
            if metadata and hasattr(metadata, 'magnification') and metadata.magnification:
                images.append((image_path, metadata))
        
        # Check if we have enough images
        if len(images) < 2:
            messagebox.showerror("Error", "Need at least 2 images with metadata for template matching")
            return
        
        # Get parameters
        method = self.method_var.get()
        threshold = self.threshold_var.get()
        multi_scale = self.multi_scale_var.get()
        use_with_maggrid = self.maggrid_var.get()
        
        # Prepare for processing
        self.stop_processing = False
        self.progress_var.set(0)
        self.status_var.set("Starting template matching...")
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert(tk.END, "Template Matching in Progress...\n\n")
        
        # Create output folder
        output_folder = os.path.join(session_folder, "template_matches")
        os.makedirs(output_folder, exist_ok=True)
        
        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_template_matching,
            args=(images, output_folder, method, threshold, multi_scale, use_with_maggrid)
        )
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _process_template_matching(self, images, output_folder, method, threshold, multi_scale, use_with_maggrid):
        """Process template matching in a separate thread."""
        try:
            # Group images by magnification
            mag_groups = {}
            for path, metadata in images:
                mag = metadata.magnification
                if mag not in mag_groups:
                    mag_groups[mag] = []
                mag_groups[mag].append((path, metadata))
            
            # Sort magnifications from high to low
            mags = sorted(mag_groups.keys(), reverse=True)
            
            # Calculate total number of pairs to check
            total_pairs = 0
            for i, high_mag in enumerate(mags):
                for j, low_mag in enumerate(mags):
                    if high_mag > low_mag:  # Only check if high_mag is actually higher than low_mag
                        total_pairs += len(mag_groups[high_mag]) * len(mag_groups[low_mag])
            
            # Update progress bar
            self.dialog.after(0, lambda: self.progress_bar.configure(maximum=total_pairs))
            
            # Results
            match_results = {}
            match_count = 0
            progress_count = 0
            
            # Process each magnification pair
            for i, high_mag in enumerate(mags):
                high_mag_images = mag_groups[high_mag]
                
                # Skip the lowest magnification (nothing lower to match against)
                if i == len(mags) - 1:
                    continue
                
                self._update_status(f"Processing {len(high_mag_images)} images at {high_mag}x magnification...")
                self._update_results(f"Processing {len(high_mag_images)} images at {high_mag}x magnification...\n")
                
                # Check against all lower magnification groups
                for low_mag in mags[i+1:]:
                    low_mag_images = mag_groups[low_mag]
                    
                    self._update_results(f"  Checking against {len(low_mag_images)} images at {low_mag}x magnification...\n")
                    
                    # Check if magnification ratio is sufficient
                    mag_ratio = high_mag / low_mag
                    if mag_ratio < 1.5:
                        self._update_results(f"  Skipping - magnification ratio ({mag_ratio:.2f}x) is too low\n")
                        continue
                    
                    # Check each high mag image against each low mag image
                    for high_path, high_metadata in high_mag_images:
                        high_name = os.path.basename(high_path)
                        
                        for low_path, low_metadata in low_mag_images:
                            # Check if processing should stop
                            if self.stop_processing:
                                self._update_status("Template matching stopped by user")
                                return
                            
                            low_name = os.path.basename(low_path)
                            progress_count += 1
                            
                            # Update progress
                            self._update_progress(progress_count)
                            
                            # Skip if mode, voltage, or spot size don't match
                            if (high_metadata.mode != low_metadata.mode or
                                high_metadata.high_voltage_kV != low_metadata.high_voltage_kV or
                                high_metadata.spot_size != low_metadata.spot_size):
                                continue
                            
                            # Check metadata-based containment
                            metadata_contained = False
                            if hasattr(low_metadata, 'check_containment'):
                                metadata_contained, _ = low_metadata.check_containment(high_metadata)
                            
                            # Try template matching
                            try:
                                is_contained, match_result = self.template_matcher.validate_containment_with_template_matching(
                                    low_path, high_path, low_metadata, high_metadata,
                                    method=method, threshold=threshold
                                )
                                
                                if is_contained:
                                    match_count += 1
                                    
                                    # Store match result
                                    match_results[(high_path, low_path)] = (is_contained, match_result)
                                    
                                    # Generate visualization
                                    vis_img = self.template_matcher.visualize_match(low_path, high_path, match_result)
                                    
                                    # Save visualization
                                    vis_filename = f"match_{high_name}_{low_name}.png"
                                    vis_path = os.path.join(output_folder, vis_filename)
                                    vis_img.save(vis_path)
                                    
                                    self._update_results(f"  Match found: {high_name} in {low_name}, "
                                                       f"score: {match_result.get('score', 0):.4f}\n")
                            except Exception as e:
                                self._update_results(f"  Error processing {high_name} in {low_name}: {str(e)}\n")
            
            # Save results to JSON
            results_dict = {
                "session": os.path.basename(os.path.dirname(output_folder)),
                "date": datetime.now().isoformat(),
                "method": method,
                "threshold": threshold,
                "multi_scale": multi_scale,
                "matches": []
            }
            
            for (high_path, low_path), (is_contained, match_result) in match_results.items():
                high_metadata = next((m for p, m in images if p == high_path), None)
                low_metadata = next((m for p, m in images if p == low_path), None)
                
                if high_metadata and low_metadata:
                    match_data = {
                        "high_mag_image": os.path.basename(high_path),
                        "low_mag_image": os.path.basename(low_path),
                        "high_mag": high_metadata.magnification,
                        "low_mag": low_metadata.magnification,
                        "mag_ratio": high_metadata.magnification / low_metadata.magnification,
                        "metadata_contained": metadata_contained,
                        "match_score": match_result.get("score", 0),
                        "match_method": match_result.get("method", method),
                        "match_scale": match_result.get("scale", 1.0),
                        "visualization": f"match_{os.path.basename(high_path)}_{os.path.basename(low_path)}.png"
                    }
                    
                    results_dict["matches"].append(match_data)
            
            # Save results
            results_path = os.path.join(output_folder, "match_results.json")
            with open(results_path, 'w') as f:
                json.dump(results_dict, f, indent=4)
            
            # Generate report
            report_path = os.path.join(output_folder, "match_report.txt")
            with open(report_path, 'w') as f:
                f.write(f"SEM Image Template Matching Report\n")
                f.write(f"=================================\n\n")
                f.write(f"Session: {os.path.basename(os.path.dirname(output_folder))}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Method: {method}\n")
                f.write(f"Threshold: {threshold}\n")
                f.write(f"Multi-scale: {'Yes' if multi_scale else 'No'}\n\n")
                
                f.write(f"Summary:\n")
                f.write(f"- Total images analyzed: {len(images)}\n")
                f.write(f"- Total matches found: {match_count} out of {progress_count} checks\n\n")
                
                # List all matches
                f.write(f"All matches:\n")
                for i, match in enumerate(results_dict["matches"]):
                    f.write(f"{i+1}. {match['high_mag_image']} ({match['high_mag']}x) in "
                           f"{match['low_mag_image']} ({match['low_mag']}x)\n")
                    f.write(f"   Score: {match['match_score']:.4f}, Scale: {match['match_scale']:.2f}x\n")
                    f.write(f"   Metadata match: {'Yes' if match.get('metadata_contained', False) else 'No'}\n")
            
            # Show results summary
            self._update_status(f"Template matching complete. Found {match_count} matches.")
            self._update_results(f"\nTemplate matching complete.\n")
            self._update_results(f"- Total images analyzed: {len(images)}\n")
            self._update_results(f"- Total matches found: {match_count} out of {progress_count} checks\n")
            self._update_results(f"- Results saved to: {output_folder}\n")
            
            # Update MagGrid workflow if requested
            if use_with_maggrid and hasattr(self.app, 'current_workflow'):
                if self.app.current_workflow.get_workflow_type() == "MagGrid":
                    # If not already using enhanced controller, create one
                    if not isinstance(self.app.current_workflow, EnhancedMagGridController):
                        self.use_enhanced_maggrid()
                    
                    # Update template matching cache
                    if isinstance(self.app.current_workflow, EnhancedMagGridController):
                        self.app.current_workflow.template_match_cache = match_results
                        
                        # Rebuild collections if needed
                        self.dialog.after(0, lambda: self._update_results(f"\nUpdating MagGrid collections with template matching results...\n"))
                        
                        # Refresh collections
                        if not self.app.current_workflow.collections:
                            self.app.current_workflow.collections = self.app.current_workflow.build_collections()
                            self.app.current_workflow.save_collections()
                        
                        # Update UI
                        if hasattr(self.app, '_update_workflow_display'):
                            self.dialog.after(0, self.app._update_workflow_display)
                        
                        self.dialog.after(0, lambda: self._update_results(f"MagGrid collections updated successfully.\n"))
        
        except Exception as e:
            self._update_status(f"Error during template matching: {str(e)}")
            self._update_results(f"\nError during template matching: {str(e)}\n")
    
    def _update_status(self, message):
        """Update the status message from a thread."""
        self.dialog.after(0, lambda: self.status_var.set(message))
    
    def _update_progress(self, value):
        """Update the progress bar from a thread."""
        self.dialog.after(0, lambda: self.progress_var.set(value))
    
    def _update_results(self, text):
        """Append text to the results widget from a thread."""
        self.dialog.after(0, lambda: self._append_results(text))
    
    def _append_results(self, text):
        """Append text to the results widget and scroll to the end."""
        self.results_text.insert(tk.END, text)
        self.results_text.see(tk.END)
    
    def stop_processing_cmd(self):
        """Stop the template matching process."""
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_processing = True
            self.status_var.set("Stopping template matching...")
            self._update_results("\nStopping template matching process...\n")
        else:
            self.status_var.set("No processing to stop")


# Code to initialize and register the plugin
def initialize_plugin(app):
    """
    Initialize the template matching plugin.
    
    Args:
        app: The main application instance
    
    Returns:
        TemplateMatchingPlugin: The plugin instance
    """
    plugin = TemplateMatchingPlugin(app)
    return plugin