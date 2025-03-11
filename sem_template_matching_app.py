import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import json
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
import logging

# Configure logging to file
logging.basicConfig(
    filename='template_matching.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filemode='w'  # 'w' overwrites existing log, 'a' would append
)

# Add console output as well (optional)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

# Now use logging instead of print
logging.info("Starting template matching...")
# logging.debug("Detailed information")
# logging.error("Error messages")
# Import the template matching helper - use the previously created class
# If the file doesn't exist, we'll include the implementation here
try:
    from template_matching import TemplateMatchingHelper
except ImportError:
    # This is the class we created earlier
    from template_matching import TemplateMatchingHelper

# Define the SEMMetadata class (based on your existing code)
class SEMMetadata:
    """Class to hold SEM image metadata."""
    
    def __init__(self, image_path=None):
        self.image_path = image_path
        self.file_name = os.path.basename(image_path) if image_path else ""
        # Image dimensions
        self.pixels_width = None
        self.pixels_height = None
        self.pixel_dimension_nm = None
        self.field_of_view_width = None  # in μm
        self.field_of_view_height = None  # in μm
        # SEM parameters
        self.magnification = None
        self.mode = None  # detector type (SED, BSD, etc.)
        self.high_voltage_kV = None
        self.spot_size = None
        # Sample positioning
        self.sample_position_x = None  # in μm
        self.sample_position_y = None  # in μm
        self.multistage_x = None
        self.multistage_y = None
        self.beam_shift_x = None
        self.beam_shift_y = None
        # Additional parameters
        self.working_distance_mm = None
        self.databar_label = None
        self.acquisition_time = None

    def extract_from_tiff(self):
        """Extract metadata from a TIFF file with embedded XML."""
        if not self.image_path or not os.path.exists(self.image_path):
            return False
            
        try:
            # Open the TIFF file using Pillow
            with Image.open(self.image_path) as img:
                # TIFF images may store metadata in tag 34683
                xml_data = img.tag_v2.get(34683)
                
                if not xml_data:
                    return False
                
                # Convert bytes to string if necessary
                if isinstance(xml_data, bytes):
                    xml_data = xml_data.decode("utf-8")
    
                # Parse the XML
                root = ET.fromstring(xml_data)
    
                # Extract basic dimensions
                self.pixels_width = int(root.find("cropHint/right").text)
                self.pixels_height = int(root.find("cropHint/bottom").text)
                self.pixel_dimension_nm = float(root.find("pixelWidth").text)
                self.field_of_view_width = self.pixel_dimension_nm * self.pixels_width / 1000  # Convert to μm
                self.field_of_view_height = self.pixel_dimension_nm * self.pixels_height / 1000  # Convert to μm
                self.magnification = int(127000 / self.field_of_view_width)  # Calculate magnification
                
                # Extract stage position information
                multi_stage = root.find("multiStage")
                self.multistage_x = None
                self.multistage_y = None
                if multi_stage:
                    for axis in multi_stage.findall("axis"):
                        if axis.get("id") == "X":
                            self.multistage_x = float(axis.text)
                        elif axis.get("id") == "Y":
                            self.multistage_y = float(axis.text)
    
                # Extract beam shift information
                beam_shift = root.find("acquisition/scan/beamShift")
                self.beam_shift_x = None
                self.beam_shift_y = None
                if beam_shift is not None:
                    self.beam_shift_x = float(beam_shift.find("x").text)
                    self.beam_shift_y = float(beam_shift.find("y").text)
    
                # Extract other metadata
                self.databar_label = root.findtext("databarLabel")
                self.acquisition_time = root.findtext("time")
                self.mode = root.find("acquisition/scan/detector").text
                self.high_voltage_kV = abs(float(root.find("acquisition/scan/highVoltage").text))
                self.working_distance_mm = float(root.find("workingDistance").text)
                self.spot_size = float(root.find("acquisition/scan/spotSize").text)
                self.sample_position_x = float(root.find("samplePosition/x").text)
                self.sample_position_y = float(root.find("samplePosition/y").text)
                
                return True
                
        except Exception as e:
            print(f"Error extracting metadata from {self.image_path}: {str(e)}")
            return False
            
    def check_containment(self, high_metadata, margin_percent=10, min_mag_ratio=1.5):
        """
        Check if high magnification image is contained within this (low magnification) image.
        
        Args:
            high_metadata: The metadata for the higher magnification image
            margin_percent: Percentage margin to require inside the boundaries (default 10%)
            min_mag_ratio: Minimum magnification ratio required (default 1.5)
            
        Returns:
            bool, str: (is_contained, reason_if_not_contained)
        """
        # Check magnification ratio
        if not self.magnification or not high_metadata.magnification:
            return False, "Missing magnification data"
            
        mag_ratio = high_metadata.magnification / self.magnification
        if mag_ratio < min_mag_ratio:
            return False, f"Insufficient magnification difference: {mag_ratio:.2f}x (need {min_mag_ratio}x)"
            
        # Check if the mode, high voltage, and spot size match
        if self.mode != high_metadata.mode:
            return False, f"Mode mismatch: {self.mode} vs {high_metadata.mode}"
            
        if self.high_voltage_kV != high_metadata.high_voltage_kV:
            return False, f"Voltage mismatch: {self.high_voltage_kV} vs {high_metadata.high_voltage_kV}"
            
        if self.spot_size != high_metadata.spot_size:
            return False, f"Spot size mismatch: {self.spot_size} vs {high_metadata.spot_size}"
            
        # Get positions and field of view dimensions
        if (not self.sample_position_x or not self.sample_position_y or 
            not self.field_of_view_width or not self.field_of_view_height or
            not high_metadata.sample_position_x or not high_metadata.sample_position_y or
            not high_metadata.field_of_view_width or not high_metadata.field_of_view_height):
            return False, "Missing position or field of view data"
            
        # Calculate boundaries of the low mag image
        low_left = self.sample_position_x - (self.field_of_view_width / 2)
        low_right = self.sample_position_x + (self.field_of_view_width / 2)
        low_top = self.sample_position_y - (self.field_of_view_height / 2)
        low_bottom = self.sample_position_y + (self.field_of_view_height / 2)
        
        # Calculate boundaries of the high mag image
        high_left = high_metadata.sample_position_x - (high_metadata.field_of_view_width / 2)
        high_right = high_metadata.sample_position_x + (high_metadata.field_of_view_width / 2)
        high_top = high_metadata.sample_position_y - (high_metadata.field_of_view_height / 2)
        high_bottom = high_metadata.sample_position_y + (high_metadata.field_of_view_height / 2)
        
        # Containment check with margin
        margin_x = self.field_of_view_width * (margin_percent / 100)
        margin_y = self.field_of_view_height * (margin_percent / 100)
        
        if high_left < (low_left + margin_x):
            return False, f"Left edge outside margin: {high_left:.2f} < {low_left + margin_x:.2f}"
            
        if high_right > (low_right - margin_x):
            return False, f"Right edge outside margin: {high_right:.2f} > {low_right - margin_x:.2f}"
            
        if high_top < (low_top + margin_y):
            return False, f"Top edge outside margin: {high_top:.2f} < {low_top + margin_y:.2f}"
            
        if high_bottom > (low_bottom - margin_y):
            return False, f"Bottom edge outside margin: {high_bottom:.2f} > {low_bottom - margin_y:.2f}"
            
        # All checks passed
        return True, None

class SEMTemplateMatchingApp:
    """Application for SEM image template matching to identify high mag images in low mag images."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("SEM Template Matching Tool")
        self.root.geometry("1280x800")
        
        # Set up template matching helper
        self.template_matcher = TemplateMatchingHelper()
        
        # Initialize data storage
        self.session_folder = None
        self.images = []  # List of (path, metadata) tuples
        self.containment_data = {}  # Format: {high_image_path: [containing_image_paths]}
        self.match_results = {}  # Format: {(high_image_path, low_image_path): match_result}
        
        # Create UI
        self._create_ui()
        
        # Initialize variables
        self.processing_thread = None
        self.stop_processing = False
    
    def _create_ui(self):
        """Create the user interface."""
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Open Session Folder", command=self._open_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Load Images", command=self._load_images).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Run Template Matching", command=self._run_template_matching).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Save Containment Data", command=self._save_containment_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop Processing", command=self._stop_processing).pack(side=tk.LEFT, padx=5)
        
        # Add method selection combobox
        ttk.Label(control_frame, text="Method:").pack(side=tk.LEFT, padx=5)
        self.method_var = tk.StringVar(value="cv2.TM_CCOEFF_NORMED")
        method_combo = ttk.Combobox(control_frame, textvariable=self.method_var, width=20)
        method_combo['values'] = list(self.template_matcher.methods.keys())
        method_combo.pack(side=tk.LEFT, padx=5)
        
        # Add threshold slider
        ttk.Label(control_frame, text="Threshold:").pack(side=tk.LEFT, padx=5)
        self.threshold_var = tk.DoubleVar(value=0.5)
        threshold_slider = ttk.Scale(control_frame, from_=0.1, to=0.9, variable=self.threshold_var, orient=tk.HORIZONTAL, length=100)
        threshold_slider.pack(side=tk.LEFT, padx=5)
        threshold_label = ttk.Label(control_frame, textvariable=self.threshold_var, width=4)
        threshold_label.pack(side=tk.LEFT)
        
        # Add multi-scale checkbox
        self.multi_scale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Multi-Scale", variable=self.multi_scale_var).pack(side=tk.LEFT, padx=5)
        
        # Add session label
        self.session_label = ttk.Label(control_frame, text="No session loaded")
        self.session_label.pack(side=tk.RIGHT, padx=5)
        
        # Create a paned window for the image panels and results
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for image selection
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # Create a frame for the image list
        image_list_frame = ttk.LabelFrame(left_frame, text="Images")
        image_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a treeview for the image list
        self.image_tree = ttk.Treeview(image_list_frame, columns=("Magnification", "Mode"), selectmode="browse")
        self.image_tree.heading("#0", text="Image")
        self.image_tree.heading("Magnification", text="Mag")
        self.image_tree.heading("Mode", text="Mode")
        self.image_tree.column("#0", width=200)
        self.image_tree.column("Magnification", width=60)
        self.image_tree.column("Mode", width=60)
        self.image_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(image_list_frame, orient=tk.VERTICAL, command=self.image_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_tree.config(yscrollcommand=scrollbar.set)
        
        # Bind image selection
        self.image_tree.bind("<<TreeviewSelect>>", self._on_image_selected)
        
        # Right panel for results
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        # Create top and bottom frames in the right panel
        top_right_frame = ttk.Frame(right_frame)
        top_right_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        bottom_right_frame = ttk.Frame(right_frame)
        bottom_right_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create image preview panels
        image_frame = ttk.Frame(top_right_frame)
        image_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left image panel (low magnification)
        left_image_frame = ttk.LabelFrame(image_frame, text="Low Magnification Image")
        left_image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.low_mag_canvas = tk.Canvas(left_image_frame, bg="black")
        self.low_mag_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right image panel (high magnification)
        right_image_frame = ttk.LabelFrame(image_frame, text="High Magnification Image")
        right_image_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.high_mag_canvas = tk.Canvas(right_image_frame, bg="black")
        self.high_mag_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results panel
        results_frame = ttk.LabelFrame(bottom_right_frame, text="Match Results")
        results_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Add a text widget for displaying results
        self.results_text = tk.Text(results_frame, height=10, width=80, wrap=tk.WORD)
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add a scrollbar
        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.config(yscrollcommand=results_scrollbar.set)
        
        # Create a frame for pair navigation
        pair_nav_frame = ttk.Frame(bottom_right_frame)
        pair_nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add combobox for selecting image pairs
        ttk.Label(pair_nav_frame, text="Match Pairs:").pack(side=tk.LEFT, padx=5)
        self.pair_var = tk.StringVar()
        self.pair_combo = ttk.Combobox(pair_nav_frame, textvariable=self.pair_var, width=50)
        self.pair_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.pair_combo.bind("<<ComboboxSelected>>", self._on_pair_selected)
        
        # Add navigation buttons
        ttk.Button(pair_nav_frame, text="Previous", command=self._previous_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(pair_nav_frame, text="Next", command=self._next_pair).pack(side=tk.LEFT, padx=5)
        
        # Add a status bar at the bottom
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add a progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
    def _open_session(self):
        """Open a session folder."""
        folder_path = filedialog.askdirectory(title="Select Session Folder")
        
        if folder_path:
            self.session_folder = folder_path
            self.session_label.config(text=f"Session: {os.path.basename(folder_path)}")
            self.status_var.set(f"Opened session: {os.path.basename(folder_path)}")
            
            # Reset UI
            self.images = []
            self.containment_data = {}
            self.match_results = {}
            self.image_tree.delete(*self.image_tree.get_children())
            self._clear_images()
            self.pair_combo['values'] = []
            self.pair_var.set("")
            self.results_text.delete('1.0', tk.END)
    
    def _load_images(self):
        """Load images with metadata from the session folder."""
        if not self.session_folder:
            messagebox.showerror("Error", "Please open a session folder first")
            return
        
        # Clear previous data
        self.images = []
        self.image_tree.delete(*self.image_tree.get_children())
        
        # Scan for images
        try:
            image_count = 0
            valid_image_count = 0
            self.status_var.set("Loading images...")
            self.root.update()
            
            for file in os.listdir(self.session_folder):
                if file.lower().endswith(('.tiff', '.tif')):
                    image_count += 1
                    file_path = os.path.join(self.session_folder, file)
                    
                    # Extract metadata
                    metadata = SEMMetadata(file_path)
                    if metadata.extract_from_tiff():
                        valid_image_count += 1
                        self.images.append((file_path, metadata))
                        
                        # Add to tree view
                        self.image_tree.insert("", "end", text=file, 
                                              values=(metadata.magnification, metadata.mode),
                                              tags=(file_path,))
                    else:
                        self.status_var.set(f"Failed to extract metadata from {file}")
            
            # Sort the tree by magnification (low to high)
            sorted_items = [(self.image_tree.set(k, "Magnification"), k) for k in self.image_tree.get_children("")]
            sorted_items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)
            
            for index, (_, item) in enumerate(sorted_items):
                self.image_tree.move(item, "", index)
            
            self.status_var.set(f"Loaded {valid_image_count} images with metadata out of {image_count} total images")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load images: {str(e)}")
    
    def _on_image_selected(self, event):
        """Handle image selection in the tree view."""
        selection = self.image_tree.selection()
        if not selection:
            return
            
        # Get the selected item
        item = selection[0]
        file_path = self.image_tree.item(item, "tags")[0]
        
        # Find the metadata
        metadata = None
        for path, meta in self.images:
            if path == file_path:
                metadata = meta
                break
        
        if not metadata:
            return
            
        # Display the image
        self._load_image_to_canvas(file_path, self.high_mag_canvas)
        
        # Check if this image has any matches
        matching_pairs = []
        for (high_path, low_path), result in self.match_results.items():
            if high_path == file_path:
                matching_pairs.append((high_path, low_path))
        
        # Update the pair combobox
        if matching_pairs:
            pair_values = []
            for high_path, low_path in matching_pairs:
                high_name = os.path.basename(high_path)
                low_name = os.path.basename(low_path)
                pair_values.append(f"{high_name} in {low_name}")
            
            self.pair_combo['values'] = pair_values
            self.pair_combo.current(0)
            self._on_pair_selected(None)
        else:
            self.pair_combo['values'] = []
            self.pair_var.set("")
            self._clear_low_mag_canvas()
            self.results_text.delete('1.0', tk.END)
            self.results_text.insert(tk.END, f"No matches found for {os.path.basename(file_path)}")
    
    def _on_pair_selected(self, event):
        """Handle pair selection in the combobox."""
        selected = self.pair_var.get()
        if not selected:
            return
            
        # Extract file names from the combo text
        parts = selected.split(" in ")
        if len(parts) != 2:
            return
            
        high_name = parts[0]
        low_name = parts[1]
        
        # Find the corresponding paths
        high_path = None
        low_path = None
        
        for path, _ in self.images:
            if os.path.basename(path) == high_name:
                high_path = path
            elif os.path.basename(path) == low_name:
                low_path = path
        
        if not high_path or not low_path:
            return
            
        # Display the images
        self._load_image_to_canvas(high_path, self.high_mag_canvas)
        self._load_image_to_canvas(low_path, self.low_mag_canvas)
        
        # Display the match result
        match_result = self.match_results.get((high_path, low_path))
        if match_result:
            self._display_match_result(high_path, low_path, match_result)
    
    def _previous_pair(self):
        """Navigate to the previous image pair."""
        values = self.pair_combo['values']
        if not values:
            return
            
        current_idx = self.pair_combo.current()
        if current_idx > 0:
            self.pair_combo.current(current_idx - 1)
            self._on_pair_selected(None)
    
    def _next_pair(self):
        """Navigate to the next image pair."""
        values = self.pair_combo['values']
        if not values:
            return
            
        current_idx = self.pair_combo.current()
        if current_idx < len(values) - 1:
            self.pair_combo.current(current_idx + 1)
            self._on_pair_selected(None)
    
    def _run_template_matching(self):
        """Run template matching on all image pairs."""
        if not self.images:
            messagebox.showerror("Error", "Please load images first")
            return
            
        # Check if there are enough images
        if len(self.images) < 2:
            messagebox.showerror("Error", "Need at least 2 images for template matching")
            return
            
        # Clear previous results
        self.match_results = {}
        
        # Get template matching parameters
        method = self.method_var.get()
        threshold = self.threshold_var.get()
        multi_scale = self.multi_scale_var.get()
        
        # Organize images by magnification
        mag_groups = {}
        for path, metadata in self.images:
            mag = metadata.magnification
            if mag not in mag_groups:
                mag_groups[mag] = []
            mag_groups[mag].append((path, metadata))
        
        # Sort magnifications from high to low
        sorted_mags = sorted(mag_groups.keys(), reverse=True)
        
        # Calculate total number of pairs to check
        total_pairs = 0
        for i, high_mag in enumerate(sorted_mags):
            for j, low_mag in enumerate(sorted_mags):
                if high_mag > low_mag:  # Only check if high_mag is actually higher than low_mag
                    total_pairs += len(mag_groups[high_mag]) * len(mag_groups[low_mag])
        
        # Update progress bar
        self.progress_var.set(0)
        self.progress_bar['maximum'] = total_pairs
        
        # Create and start the processing thread
        self.stop_processing = False
        self.processing_thread = threading.Thread(
            target=self._process_template_matching,
            args=(mag_groups, sorted_mags, method, threshold, multi_scale)
        )
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _process_template_matching(self, mag_groups, sorted_mags, method, threshold, multi_scale):
        """
        Process template matching in a separate thread.
        
        Args:
            mag_groups: Dictionary mapping magnifications to lists of (path, metadata) tuples
            sorted_mags: List of magnifications sorted from high to low
            method: OpenCV template matching method
            threshold: Matching threshold
            multi_scale: Whether to use multi-scale template matching
        """
        try:
            # Initialize progress counter
            progress_count = 0
            match_count = 0
            
            # Process each magnification pair
            for i, high_mag in enumerate(sorted_mags):
                for j, low_mag in enumerate(sorted_mags):
                    # Only check if high_mag is actually higher than low_mag
                    if high_mag <= low_mag:
                        continue
                        
                    # Check all image pairs with these magnifications
                    for high_path, high_metadata in mag_groups[high_mag]:
                        for low_path, low_metadata in mag_groups[low_mag]:
                            # Check if processing should stop
                            if self.stop_processing:
                                return
                                
                            # Update progress
                            progress_count += 1
                            self._update_progress(progress_count, f"Checking pair {progress_count}/{total_pairs}")
                            
                            # Check containment using template matching
                            try:
                                is_contained, match_result = self.template_matcher.validate_containment_with_template_matching(
                                    low_path, high_path, low_metadata, high_metadata, method, threshold
                                )
                                
                                if is_contained and match_result:
                                    match_count += 1
                                    self.match_results[(high_path, low_path)] = match_result
                                    
                                    # Store in containment data
                                    if high_path not in self.containment_data:
                                        self.containment_data[high_path] = []
                                    self.containment_data[high_path].append(low_path)
                            except Exception as e:
                                print(f"Error matching {os.path.basename(high_path)} in {os.path.basename(low_path)}: {str(e)}")
            
            # Update UI
            self._update_ui_after_matching(match_count)
            
        except Exception as e:
            # Handle any exceptions
            self._update_status(f"Error during template matching: {str(e)}")
    
    def _update_progress(self, value, message):
        """Update the progress bar and status message from a thread."""
        self.root.after(0, lambda: self.progress_var.set(value))
        self.root.after(0, lambda: self.status_var.set(message))
    
    def _update_status(self, message):
        """Update the status message from a thread."""
        self.root.after(0, lambda: self.status_var.set(message))
    
    def _update_ui_after_matching(self, match_count):
        """Update the UI after template matching is complete."""
        self.root.after(0, lambda: self._update_ui_after_matching_impl(match_count))
    
    def _update_ui_after_matching_impl(self, match_count):
        """Implementation of UI update after template matching."""
        self.status_var.set(f"Template matching complete. Found {match_count} matches.")
        self.progress_var.set(0)
        
        # Update the image tree with match information
        for item in self.image_tree.get_children():
            file_path = self.image_tree.item(item, "tags")[0]
            
            # Check if this image has any matches
            match_count = 0
            for (high_path, _) in self.match_results.keys():
                if high_path == file_path:
                    match_count += 1
            
            if match_count > 0:
                # Update the item text to indicate matches
                current_values = self.image_tree.item(item, "values")
                self.image_tree.item(item, values=(current_values[0], current_values[1], f"{match_count} matches"))
        
        # Show a message box with results
        messagebox.showinfo("Template Matching Complete", 
                          f"Found {match_count} matches across {len(self.containment_data)} high magnification images.")
    
    def _stop_processing(self):
        """Stop the template matching process."""
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_processing = True
            self.status_var.set("Stopping processing...")
        else:
            self.status_var.set("No processing to stop")
    
    def _clear_images(self):
        """Clear both image canvases."""
        self.low_mag_canvas.delete("all")
        self.high_mag_canvas.delete("all")
    
    def _clear_low_mag_canvas(self):
        """Clear the low magnification canvas."""
        self.low_mag_canvas.delete("all")
    
    def _load_image_to_canvas(self, image_path, canvas):
        """Load an image onto the specified canvas."""
        try:
            # Open the image
            img = Image.open(image_path)
            
            # Resize to fit canvas
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            # If canvas size is not available yet, use a default
            if canvas_width <= 1:
                canvas_width = 400
            if canvas_height <= 1:
                canvas_height = 400
            
            # Calculate resize ratio
            img_ratio = img.width / img.height
            canvas_ratio = canvas_width / canvas_height
            
            if img_ratio > canvas_ratio:
                # Image is wider than canvas
                new_width = canvas_width
                new_height = int(canvas_width / img_ratio)
            else:
                # Image is taller than canvas
                new_height = canvas_height
                new_width = int(canvas_height * img_ratio)
            
            # Resize image
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(resized_img)
            
            # Clear canvas
            canvas.delete("all")
            
            # Display image
            canvas.create_image(canvas_width // 2, canvas_height // 2, anchor=tk.CENTER, image=photo)
            
            # Keep a reference to prevent garbage collection
            canvas.image = photo
            
            # Find metadata to display magnification
            for path, metadata in self.images:
                if path == image_path and metadata.magnification:
                    canvas.create_text(10, 10, anchor=tk.NW, text=f"Mag: {metadata.magnification}x", 
                                     fill="white", font=("Arial", 12))
                    break
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def _display_match_result(self, high_path, low_path, match_result):
        """Display match result in the text widget and overlay on canvas."""
        self.results_text.delete('1.0', tk.END)
        
        # Display basic match information
        high_name = os.path.basename(high_path)
        low_name = os.path.basename(low_path)
        
        self.results_text.insert(tk.END, f"Match Details: {high_name} in {low_name}\n\n")
        self.results_text.insert(tk.END, f"Match Method: {match_result.get('method', 'Unknown')}\n")
        self.results_text.insert(tk.END, f"Match Score: {match_result.get('score', 0):.4f}\n")
        
        if 'scale' in match_result:
            self.results_text.insert(tk.END, f"Scale Factor: {match_result['scale']:.4f}\n")
        
        # Add position information
        if 'top_left' in match_result and 'bottom_right' in match_result:
            x1, y1 = match_result['top_left']
            x2, y2 = match_result['bottom_right']
            
            self.results_text.insert(tk.END, f"\nBounding Box:\n")
            self.results_text.insert(tk.END, f"  Top-Left: ({x1}, {y1})\n")
            self.results_text.insert(tk.END, f"  Bottom-Right: ({x2}, {y2})\n")
            self.results_text.insert(tk.END, f"  Width: {x2 - x1} pixels\n")
            self.results_text.insert(tk.END, f"  Height: {y2 - y1} pixels\n")
            
            # Get center position
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            self.results_text.insert(tk.END, f"  Center: ({cx}, {cy})\n")
        
        # Add metadata comparison if available
        high_metadata = None
        low_metadata = None
        
        for path, metadata in self.images:
            if path == high_path:
                high_metadata = metadata
            elif path == low_path:
                low_metadata = metadata
        
        if high_metadata and low_metadata:
            self.results_text.insert(tk.END, f"\nMetadata Comparison:\n")
            self.results_text.insert(tk.END, f"  High Mag: {high_metadata.magnification}x, Mode: {high_metadata.mode}\n")
            self.results_text.insert(tk.END, f"  Low Mag: {low_metadata.magnification}x, Mode: {low_metadata.mode}\n")
            
            # Calculate magnification ratio
            if high_metadata.magnification and low_metadata.magnification:
                ratio = high_metadata.magnification / low_metadata.magnification
                self.results_text.insert(tk.END, f"  Mag Ratio: {ratio:.2f}x\n")
            
            # Calculate position difference
            if (high_metadata.sample_position_x and high_metadata.sample_position_y and
                low_metadata.sample_position_x and low_metadata.sample_position_y):
                dx = high_metadata.sample_position_x - low_metadata.sample_position_x
                dy = high_metadata.sample_position_y - low_metadata.sample_position_y
                distance = (dx**2 + dy**2)**0.5
                self.results_text.insert(tk.END, f"  Position Difference: {distance:.2f} μm\n")
        
        # Draw bounding box on low mag canvas
        if 'top_left' in match_result and 'bottom_right' in match_result:
            self._draw_match_overlay(match_result)
    
    def _draw_match_overlay(self, match_result):
        """Draw the match overlay on the low mag canvas."""
        # Get canvas dimensions
        canvas_width = self.low_mag_canvas.winfo_width()
        canvas_height = self.low_mag_canvas.winfo_height()
        
        # Get image dimensions
        if hasattr(self.low_mag_canvas, 'image') and hasattr(self.low_mag_canvas.image, 'width'):
            img_width = self.low_mag_canvas.image.width()
            img_height = self.low_mag_canvas.image.height()
        else:
            # Default to canvas size if no image
            img_width = canvas_width
            img_height = canvas_height
        
        # Calculate scaling factors
        scale_x = img_width / self.low_mag_canvas.image.width()
        scale_y = img_height / self.low_mag_canvas.image.height()
        
        # Get match coordinates
        x1, y1 = match_result['top_left']
        x2, y2 = match_result['bottom_right']
        
        # Scale coordinates to canvas size
        x1_scaled = x1 * scale_x
        y1_scaled = y1 * scale_y
        x2_scaled = x2 * scale_x
        y2_scaled = y2 * scale_y
        
        # Calculate offset to center the image in the canvas
        offset_x = (canvas_width - img_width) / 2
        offset_y = (canvas_height - img_height) / 2
        
        # Adjust coordinates with offset
        x1_canvas = x1_scaled + offset_x
        y1_canvas = y1_scaled + offset_y
        x2_canvas = x2_scaled + offset_x
        y2_canvas = y2_scaled + offset_y
        
        # Draw rectangle
        self.low_mag_canvas.create_rectangle(
            x1_canvas, y1_canvas, x2_canvas, y2_canvas,
            outline="red", width=2
        )
    
    def _save_containment_data(self):
        """Save containment data to file."""
        if not self.containment_data:
            messagebox.showinfo("Info", "No containment data to save")
            return
        
        # Ask for save location
        save_path = filedialog.asksaveasfilename(
            title="Save Containment Data",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if save_path:
            try:
                # Convert to serializable format with additional metadata
                serializable_data = {}
                for high_path, container_paths in self.containment_data.items():
                    high_rel_path = os.path.basename(high_path)
                    high_metadata = next((m for p, m in self.images if p == high_path), None)
                    
                    if high_metadata:
                        high_data = {
                            "filename": high_rel_path,
                            "magnification": high_metadata.magnification,
                            "position_x": high_metadata.sample_position_x,
                            "position_y": high_metadata.sample_position_y,
                            "fov_width": high_metadata.field_of_view_width,
                            "fov_height": high_metadata.field_of_view_height,
                            "mode": high_metadata.mode,
                            "high_voltage_kV": high_metadata.high_voltage_kV,
                            "spot_size": high_metadata.spot_size,
                            "containers": []
                        }
                        
                        for container_path in container_paths:
                            container_rel_path = os.path.basename(container_path)
                            container_metadata = next((m for p, m in self.images if p == container_path), None)
                            
                            if container_metadata:
                                container_data = {
                                    "filename": container_rel_path,
                                    "magnification": container_metadata.magnification,
                                    "position_x": container_metadata.sample_position_x,
                                    "position_y": container_metadata.sample_position_y,
                                    "fov_width": container_metadata.field_of_view_width,
                                    "fov_height": container_metadata.field_of_view_height
                                }
                                
                                # Add match info if available
                                match_result = self.match_results.get((high_path, container_path))
                                if match_result:
                                    match_data = {
                                        "score": match_result.get("score"),
                                        "method": match_result.get("method"),
                                        "scale": match_result.get("scale"),
                                        "bbox": {
                                            "top_left": match_result.get("top_left"),
                                            "bottom_right": match_result.get("bottom_right")
                                        }
                                    }
                                    container_data["match_info"] = match_data
                                
                                high_data["containers"].append(container_data)
                            else:
                                high_data["containers"].append({"filename": container_rel_path})
                        
                        serializable_data[high_rel_path] = high_data
                    else:
                        # Fallback if metadata not available
                        serializable_data[high_rel_path] = {
                            "filename": high_rel_path,
                            "containers": [{"filename": os.path.basename(p)} for p in container_paths]
                        }
                
                # Save to file
                with open(save_path, 'w') as f:
                    json.dump(serializable_data, f, indent=4)
                
                # Also save a summary report
                report_path = save_path.replace(".json", "_report.txt")
                with open(report_path, 'w') as f:
                    f.write(f"SEM Image Template Matching Report\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Session: {os.path.basename(self.session_folder)}\n\n")
                    
                    f.write(f"Summary:\n")
                    f.write(f"- Total images analyzed: {len(self.images)}\n")
                    f.write(f"- High mag images with matches: {len(self.containment_data)}\n")
                    f.write(f"- Total containment relationships: {sum(len(containers) for containers in self.containment_data.values())}\n\n")
                    
                    # Group by magnification levels
                    mag_levels = {}
                    for path, metadata in self.images:
                        mag = metadata.magnification
                        if mag not in mag_levels:
                            mag_levels[mag] = []
                        mag_levels[mag].append((path, metadata))
                    
                    # List magnification levels
                    f.write(f"Magnification Levels:\n")
                    for mag in sorted(mag_levels.keys()):
                        f.write(f"- {mag}x: {len(mag_levels[mag])} images\n")
                    f.write("\n")
                    
                    # List containment chains (paths from high to low magnification)
                    f.write(f"Containment Chains:\n")
                    chain_count = 0
                    
                    # Start with highest magnification images
                    high_mags = sorted(mag_levels.keys(), reverse=True)
                    if high_mags:
                        for high_path, high_metadata in mag_levels[high_mags[0]]:
                            if high_path in self.containment_data:
                                chain_count += 1
                                f.write(f"Chain {chain_count}:\n")
                                
                                # Build chain
                                chain = [high_path]
                                current = high_path
                                
                                while current in self.containment_data and self.containment_data[current]:
                                    # For simplicity, just take the first container
                                    container = self.containment_data[current][0]
                                    chain.append(container)
                                    current = container
                                
                                # Print chain with detailed position and FOV info
                                for i, path in enumerate(chain):
                                    filename = os.path.basename(path)
                                    metadata = next((m for p, m in self.images if p == path), None)
                                    
                                    if metadata:
                                        mag = metadata.magnification
                                        pos_x = metadata.sample_position_x
                                        pos_y = metadata.sample_position_y
                                        fov_w = metadata.field_of_view_width
                                        fov_h = metadata.field_of_view_height
                                        
                                        f.write(f"  {i+1}. {filename} ({mag}x)\n")
                                        f.write(f"     Position: ({pos_x:.2f}, {pos_y:.2f}) μm\n")
                                        f.write(f"     Field of View: {fov_w:.2f} x {fov_h:.2f} μm\n")
                                        
                                        # Add match info if available and not the first in chain
                                        if i > 0:
                                            prev_path = chain[i-1]
                                            match_result = self.match_results.get((prev_path, path))
                                            if match_result:
                                                f.write(f"     Match Score: {match_result.get('score', 0):.4f}\n")
                                                if 'scale' in match_result:
                                                    f.write(f"     Scale Factor: {match_result['scale']:.4f}\n")
                                    else:
                                        f.write(f"  {i+1}. {filename} (metadata unavailable)\n")
                                    
                                f.write("\n")
                
                self.status_var.set(f"Saved containment data to {save_path} and {report_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save containment data: {str(e)}")

def main():
    """Main entry point."""
    root = tk.Tk()
    app = SEMTemplateMatchingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
