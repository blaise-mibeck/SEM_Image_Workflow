import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import json
import csv
import xml.etree.ElementTree as ET

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


class SEMContainmentTester:
    """A tool to verify containment relationships between SEM images."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("SEM Image Containment Tester")
        self.root.geometry("1200x800")
        
        # Data storage
        self.session_folder = None
        self.images = []  # List of (path, metadata) tuples
        self.containment_data = {}  # Format: {high_image_path: [containing_image_paths]}
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create the user interface."""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Open Session Folder", command=self._open_session).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Load Images", command=self._load_images).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Auto-Detect Containment", command=self._auto_detect_containment).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Save Containment Data", command=self._save_containment_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Load Containment Data", command=self._load_containment_data).pack(side=tk.LEFT, padx=5)
        
        # Add a label to display the current session
        self.session_label = ttk.Label(control_frame, text="No session loaded")
        self.session_label.pack(side=tk.RIGHT, padx=5)
        
        # Create image panels
        image_frame = ttk.Frame(main_frame)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for first image
        left_frame = ttk.LabelFrame(image_frame, text="Potential Container Image")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Image selector for left panel
        self.left_image_var = tk.StringVar()
        ttk.Label(left_frame, text="Select Image:").pack(anchor=tk.W, padx=5, pady=5)
        self.left_image_combo = ttk.Combobox(left_frame, textvariable=self.left_image_var, state="readonly")
        self.left_image_combo.pack(fill=tk.X, padx=5, pady=5)
        self.left_image_combo.bind("<<ComboboxSelected>>", self._on_left_image_selected)
        
        # Metadata display for left panel
        self.left_metadata_text = tk.Text(left_frame, height=8, width=40)
        self.left_metadata_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Image canvas for left panel
        self.left_canvas = tk.Canvas(left_frame, bg="black")
        self.left_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right panel for second image
        right_frame = ttk.LabelFrame(image_frame, text="Potential Contained Image")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Image selector for right panel
        self.right_image_var = tk.StringVar()
        ttk.Label(right_frame, text="Select Image:").pack(anchor=tk.W, padx=5, pady=5)
        self.right_image_combo = ttk.Combobox(right_frame, textvariable=self.right_image_var, state="readonly")
        self.right_image_combo.pack(fill=tk.X, padx=5, pady=5)
        self.right_image_combo.bind("<<ComboboxSelected>>", self._on_right_image_selected)
        
        # Metadata display for right panel
        self.right_metadata_text = tk.Text(right_frame, height=8, width=40)
        self.right_metadata_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Image canvas for right panel
        self.right_canvas = tk.Canvas(right_frame, bg="black")
        self.right_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Containment check result
        self.containment_result_var = tk.StringVar(value="")
        containment_result_label = ttk.Label(main_frame, textvariable=self.containment_result_var, font=("Arial", 12))
        containment_result_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Bottom panel for containment decisions
        decision_frame = ttk.Frame(main_frame)
        decision_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(decision_frame, text="Is the right image contained within the left image?").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(decision_frame, text="Yes", command=lambda: self._record_containment(True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(decision_frame, text="No", command=lambda: self._record_containment(False)).pack(side=tk.LEFT, padx=5)
        ttk.Button(decision_frame, text="Skip", command=self._skip_pair).pack(side=tk.LEFT, padx=5)
        
        # Add margin slider
        ttk.Label(decision_frame, text="Margin %:").pack(side=tk.LEFT, padx=5)
        self.margin_var = tk.IntVar(value=10)
        margin_slider = ttk.Scale(decision_frame, from_=0, to=20, variable=self.margin_var, orient=tk.HORIZONTAL)
        margin_slider.pack(side=tk.LEFT, padx=5)
        margin_slider.bind("<ButtonRelease-1>", self._on_margin_changed)
        ttk.Label(decision_frame, textvariable=self.margin_var).pack(side=tk.LEFT)
        
        # Add progress indicator
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(decision_frame, textvariable=self.progress_var).pack(side=tk.RIGHT, padx=5)
        
        # Add status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
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
            self.left_image_combo['values'] = []
            self.right_image_combo['values'] = []
            self._clear_images()
    
    def _load_images(self):
        """Load images with metadata from the session folder."""
        if not self.session_folder:
            messagebox.showerror("Error", "Please open a session folder first")
            return
        
        # Clear previous data
        self.images = []
        
        # Scan for images
        try:
            for file in os.listdir(self.session_folder):
                if file.lower().endswith(('.tiff', '.tif')):
                    file_path = os.path.join(self.session_folder, file)
                    
                    # Extract metadata
                    metadata = SEMMetadata(file_path)
                    if metadata.extract_from_tiff():
                        self.images.append((file_path, metadata))
                    else:
                        self.status_var.set(f"Failed to extract metadata from {file}")
            
            # Sort by magnification (low to high)
            self.images.sort(key=lambda x: x[1].magnification or 0)
            
            # Update UI
            self._update_image_selectors()
            
            self.status_var.set(f"Loaded {len(self.images)} images with metadata")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load images: {str(e)}")
    
    def _update_image_selectors(self):
        """Update the image selector comboboxes."""
        if not self.images:
            return
        
        # Create strings for display
        image_options = []
        for path, metadata in self.images:
            filename = os.path.basename(path)
            mag = metadata.magnification or "Unknown"
            option = f"{filename} ({mag}x)"
            image_options.append(option)
        
        # Update comboboxes
        self.left_image_combo['values'] = image_options
        self.right_image_combo['values'] = image_options
        
        # Select first item by default
        if image_options:
            self.left_image_combo.current(0)
            self.right_image_combo.current(min(1, len(image_options) - 1))
            
            # Display initial images
            self._on_left_image_selected(None)
            self._on_right_image_selected(None)
            
            # Check containment
            self._check_current_containment()
    
    def _on_left_image_selected(self, event):
        """Handle left image selection."""
        selected = self.left_image_var.get()
        if selected:
            # Extract the filename from the combo box text
            filename = selected.split(" (")[0]
            
            # Find the corresponding image path and metadata
            for path, metadata in self.images:
                if os.path.basename(path) == filename:
                    self._load_image_to_canvas(path, self.left_canvas)
                    self._display_metadata(metadata, self.left_metadata_text)
                    break
            
            # Check containment for current pair
            self._check_current_containment()
    
    def _on_right_image_selected(self, event):
        """Handle right image selection."""
        selected = self.right_image_var.get()
        if selected:
            # Extract the filename from the combo box text
            filename = selected.split(" (")[0]
            
            # Find the corresponding image path and metadata
            for path, metadata in self.images:
                if os.path.basename(path) == filename:
                    self._load_image_to_canvas(path, self.right_canvas)
                    self._display_metadata(metadata, self.right_metadata_text)
                    break
            
            # Check containment for current pair
            self._check_current_containment()
    
    def _on_margin_changed(self, event):
        """Handle margin slider change."""
        # Check containment with new margin
        self._check_current_containment()
    
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
    
    def _display_metadata(self, metadata, text_widget):
        """Display metadata in the text widget."""
        text_widget.delete("1.0", tk.END)
        
        if not metadata:
            text_widget.insert(tk.END, "No metadata available")
            return
        
        # Format metadata for display
        text_widget.insert(tk.END, f"Magnification: {metadata.magnification}x\n")
        text_widget.insert(tk.END, f"Mode: {metadata.mode}\n")
        text_widget.insert(tk.END, f"High Voltage: {metadata.high_voltage_kV} kV\n")
        text_widget.insert(tk.END, f"Spot Size: {metadata.spot_size}\n")
        text_widget.insert(tk.END, f"Position: ({metadata.sample_position_x:.2f}, {metadata.sample_position_y:.2f}) µm\n")
        text_widget.insert(tk.END, f"Field of View: {metadata.field_of_view_width:.2f} x {metadata.field_of_view_height:.2f} µm\n")
        
        # Make read-only
        text_widget.config(state=tk.DISABLED)
    
    def _check_current_containment(self):
        """Check if the right image is contained within the left image."""
        # Get current selected images
        left_selected = self.left_image_var.get()
        right_selected = self.right_image_var.get()
        
        if not left_selected or not right_selected:
            self.containment_result_var.set("")
            return
        
        # Extract filenames
        left_filename = left_selected.split(" (")[0]
        right_filename = right_selected.split(" (")[0]
        
        # Find corresponding metadata
        left_metadata = None
        right_metadata = None
        left_path = None
        right_path = None
        
        for path, metadata in self.images:
            if os.path.basename(path) == left_filename:
                left_metadata = metadata
                left_path = path
            if os.path.basename(path) == right_filename:
                right_metadata = metadata
                right_path = path
        
        if not left_metadata or not right_metadata:
            self.containment_result_var.set("Cannot check containment: Missing metadata")
            return
        
        # Check if they're the same image
        if left_path == right_path:
            self.containment_result_var.set("Same image selected on both sides")
            return
        
        # Check containment
        margin = self.margin_var.get()
        is_contained, reason = left_metadata.check_containment(right_metadata, margin_percent=margin)
        
        if is_contained:
            self.containment_result_var.set("✅ Right image IS contained within left image")
            
            # Check if this relationship is recorded
            if right_path in self.containment_data and left_path in self.containment_data[right_path]:
                self.containment_result_var.set(self.containment_result_var.get() + " (Recorded)")
        else:
            self.containment_result_var.set(f"❌ Right image is NOT contained within left image: {reason}")
            
            # Check if this negative relationship is recorded (by absence)
            if right_path in self.containment_data and left_path not in self.containment_data[right_path]:
                self.containment_result_var.set(self.containment_result_var.get() + " (Recorded)")
    
    def _clear_images(self):
        """Clear both image canvases."""
        self.left_canvas.delete("all")
        self.right_canvas.delete("all")
        self.left_canvas.image = None
        self.right_canvas.image = None
        self.left_metadata_text.config(state=tk.NORMAL)
        self.right_metadata_text.config(state=tk.NORMAL)
        self.left_metadata_text.delete("1.0", tk.END)
        self.right_metadata_text.delete("1.0", tk.END)
        self.left_metadata_text.config(state=tk.DISABLED)
        self.right_metadata_text.config(state=tk.DISABLED)
        self.containment_result_var.set("")
    
    def _record_containment(self, contained):
        """Record containment relationship."""
        # Get current selected images
        left_selected = self.left_image_var.get()
        right_selected = self.right_image_var.get()
        
        if not left_selected or not right_selected:
            messagebox.showerror("Error", "Please select both images")
            return
        
        # Extract filenames
        left_filename = left_selected.split(" (")[0]
        right_filename = right_selected.split(" (")[0]
        
        # Find corresponding image paths
        left_path = None
        right_path = None
        
        for path, metadata in self.images:
            if os.path.basename(path) == left_filename:
                left_path = path
            if os.path.basename(path) == right_filename:
                right_path = path
        
        if left_path and right_path:
            # Record the relationship
            if contained:
                if right_path not in self.containment_data:
                    self.containment_data[right_path] = []
                
                if left_path not in self.containment_data[right_path]:
                    self.containment_data[right_path].append(left_path)
                    self.status_var.set(f"Recorded: {os.path.basename(right_path)} is contained within {os.path.basename(left_path)}")
            else:
                # If relationship exists, remove it
                if right_path in self.containment_data and left_path in self.containment_data[right_path]:
                    self.containment_data[right_path].remove(left_path)
                    if not self.containment_data[right_path]:
                        del self.containment_data[right_path]
                    self.status_var.set(f"Recorded: {os.path.basename(right_path)} is NOT contained within {os.path.basename(left_path)}")
            
            # Update progress
            self._update_progress()
            
            # Update containment check display
            self._check_current_containment()
            
            # Move to next pair
            self._move_to_next_pair()
    
    def _skip_pair(self):
        """Skip the current image pair."""
        self._move_to_next_pair()
    
    def _move_to_next_pair(self):
        """Move to the next image pair."""
        # Get current indices
        left_idx = self.left_image_combo.current()
        right_idx = self.right_image_combo.current()
        
        # Total number of images
        num_images = len(self.images)
        
        # Move to next pair
        right_idx += 1
        if right_idx >= num_images:
            right_idx = 0
            left_idx += 1
            if left_idx >= num_images:
                left_idx = 0
        
        # Skip identical pairs
        if left_idx == right_idx:
            right_idx += 1
            if right_idx >= num_images:
                right_idx = 0
        
        # Update comboboxes
        self.left_image_combo.current(left_idx)
        self.right_image_combo.current(right_idx)
        
        # Update images
        self._on_left_image_selected(None)
        self._on_right_image_selected(None)
    
    def _update_progress(self):
        """Update progress indicator."""
        total_pairs = len(self.images) * (len(self.images) - 1)
        recorded_pairs = sum(len(containers) for containers in self.containment_data.values())
        
        self.progress_var.set(f"Progress: {recorded_pairs}/{total_pairs} pairs recorded")
    
    def _auto_detect_containment(self):
        """Automatically detect containment relationships."""
        if not self.images:
            messagebox.showerror("Error", "Please load images first")
            return
        
        # Clear existing containment data
        if self.containment_data and messagebox.askyesno("Confirm", "This will clear existing containment data. Continue?") == False:
            return
            
        self.containment_data = {}
        
        # Get current margin setting
        margin = self.margin_var.get()
        
        # Check each possible pair
        detected_count = 0
        total_checks = 0
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Detecting Containment")
        progress_window.geometry("300x100")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Add progress bar
        progress_label = ttk.Label(progress_window, text="Analyzing image pairs...")
        progress_label.pack(pady=10)
        progress_bar = ttk.Progressbar(progress_window, orient=tk.HORIZONTAL, length=280, mode='determinate')
        progress_bar.pack(padx=10)
        
        # Calculate total pairs to check
        total_pairs = len(self.images) * (len(self.images) - 1)
        progress_bar['maximum'] = total_pairs
        
        # Update progress at regular intervals
        def update_progress():
            progress_bar['value'] = total_checks
            progress_label.config(text=f"Analyzing: {total_checks}/{total_pairs} pairs checked, {detected_count} contained")
            progress_window.update()
        
        try:
            # Check all pairs
            for i, (high_path, high_metadata) in enumerate(self.images):
                for j, (low_path, low_metadata) in enumerate(self.images):
                    # Skip same image
                    if i == j:
                        continue
                    
                    # Update progress
                    total_checks += 1
                    if total_checks % 10 == 0:  # Update every 10 checks to avoid UI slowdowns
                        update_progress()
                    
                    # Check if high mag image is contained within low mag image
                    is_contained, _ = low_metadata.check_containment(high_metadata, margin_percent=margin)
                    
                    if is_contained:
                        if high_path not in self.containment_data:
                            self.containment_data[high_path] = []
                        self.containment_data[high_path].append(low_path)
                        detected_count += 1
            
            # Final progress update
            update_progress()
            
            # Close progress window after a short delay
            self.root.after(500, progress_window.destroy)
            
            # Update UI
            self._update_progress()
            self._check_current_containment()
            
            # Show results
            messagebox.showinfo("Auto-Detection Complete", 
                               f"Detected {detected_count} containment relationships out of {total_pairs} possible pairs.")
            
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Error", f"Error during auto-detection: {str(e)}")
    
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
                
                # Also save as CSV for easier viewing with position and FOV data
                csv_path = save_path.replace(".json", ".csv")
                with open(csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Contained Image", "Container Image", 
                        "Contained Mag", "Container Mag",
                        "Contained Pos X", "Contained Pos Y", 
                        "Container Pos X", "Container Pos Y",
                        "Contained FOV Width", "Contained FOV Height", 
                        "Container FOV Width", "Container FOV Height"
                    ])
                    
                    for high_path, container_paths in self.containment_data.items():
                        high_rel_path = os.path.basename(high_path)
                        high_metadata = next((m for p, m in self.images if p == high_path), None)
                        
                        if high_metadata:
                            high_mag = high_metadata.magnification
                            high_pos_x = high_metadata.sample_position_x
                            high_pos_y = high_metadata.sample_position_y
                            high_fov_w = high_metadata.field_of_view_width
                            high_fov_h = high_metadata.field_of_view_height
                        else:
                            high_mag = "Unknown"
                            high_pos_x = high_pos_y = high_fov_w = high_fov_h = "Unknown"
                        
                        for container_path in container_paths:
                            container_rel_path = os.path.basename(container_path)
                            container_metadata = next((m for p, m in self.images if p == container_path), None)
                            
                            if container_metadata:
                                container_mag = container_metadata.magnification
                                container_pos_x = container_metadata.sample_position_x
                                container_pos_y = container_metadata.sample_position_y
                                container_fov_w = container_metadata.field_of_view_width
                                container_fov_h = container_metadata.field_of_view_height
                            else:
                                container_mag = "Unknown"
                                container_pos_x = container_pos_y = container_fov_w = container_fov_h = "Unknown"
                            
                            writer.writerow([
                                high_rel_path, container_rel_path, 
                                high_mag, container_mag,
                                high_pos_x, high_pos_y, 
                                container_pos_x, container_pos_y,
                                high_fov_w, high_fov_h, 
                                container_fov_w, container_fov_h
                            ])
                
                # Generate a readable report
                report_path = save_path.replace(".json", "_report.txt")
                with open(report_path, 'w') as f:
                    f.write(f"SEM Image Containment Report\n")
                    f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Session: {os.path.basename(self.session_folder)}\n\n")
                    
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
                                    else:
                                        f.write(f"  {i+1}. {filename} (metadata unavailable)\n")
                                    
                                f.write("\n")
                    
                self.status_var.set(f"Saved containment data to {save_path}, {csv_path}, and {report_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save containment data: {str(e)}")
    
    def _load_containment_data(self):
        """Load containment data from file."""
        # Ask for file location
        load_path = filedialog.askopenfilename(
            title="Load Containment Data",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if load_path:
            try:
                # Load from file
                with open(load_path, 'r') as f:
                    serialized_data = json.load(f)
                
                # Convert to internal format (use full paths)
                self.containment_data = {}
                for high_rel_path, container_rel_paths in serialized_data.items():
                    # Find matching full paths
                    high_full_path = None
                    container_full_paths = []
                    
                    for path, _ in self.images:
                        if os.path.basename(path) == high_rel_path:
                            high_full_path = path
                        
                        if os.path.basename(path) in container_rel_paths:
                            container_full_paths.append(path)
                    
                    if high_full_path:
                        self.containment_data[high_full_path] = container_full_paths
                
                self.status_var.set(f"Loaded containment data from {load_path}")
                self._update_progress()
                self._check_current_containment()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load containment data: {str(e)}")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = SEMContainmentTester(root)
    root.mainloop()


if __name__ == "__main__":
    main()