"""
ImageMetadata module for SEM images.
"""
import os

class ImageMetadata:
    """Stores metadata extracted from SEM images."""
    
    def __init__(self, image_path):
        self.image_path = image_path
        self.filename = os.path.basename(image_path)
        
        # Basic metadata
        self.databar_label = None
        self.acquisition_time = None
        
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
        self.working_distance_mm = None
        self.spot_size = None
        self.dwell_time_ns = None
        
        # Sample positioning
        self.sample_position_x = None  # in μm
        self.sample_position_y = None  # in μm
        self.multistage_x = None
        self.multistage_y = None
        self.beam_shift_x = None
        self.beam_shift_y = None
        
        # Image adjustments
        self.contrast = None
        self.brightness = None
        self.gamma = None
        
        # Additional parameters
        self.pressure_Pa = None
        self.emission_current_uA = None
        
        # Any other metadata
        self.additional_params = {}
    
    def is_valid(self):
        """Check if metadata has required fields for workflow processing."""
        required_fields = [
            self.mode, 
            self.high_voltage_kV, 
            self.magnification,
            self.field_of_view_width, 
            self.field_of_view_height,
            self.sample_position_x, 
            self.sample_position_y
        ]
        return all(field is not None for field in required_fields)
    
    def to_dict(self):
        """Convert metadata to dictionary for storage."""
        data = {
            "image_path": self.image_path,
            "filename": self.filename,
            "databar_label": self.databar_label,
            "acquisition_time": self.acquisition_time,
            "pixels_width": self.pixels_width,
            "pixels_height": self.pixels_height,
            "pixel_dimension_nm": self.pixel_dimension_nm,
            "field_of_view_width": self.field_of_view_width,
            "field_of_view_height": self.field_of_view_height,
            "magnification": self.magnification,
            "mode": self.mode,
            "high_voltage_kV": self.high_voltage_kV,
            "working_distance_mm": self.working_distance_mm,
            "spot_size": self.spot_size,
            "dwell_time_ns": self.dwell_time_ns,
            "sample_position_x": self.sample_position_x,
            "sample_position_y": self.sample_position_y,
            "multistage_x": self.multistage_x,
            "multistage_y": self.multistage_y,
            "beam_shift_x": self.beam_shift_x,
            "beam_shift_y": self.beam_shift_y,
            "contrast": self.contrast,
            "brightness": self.brightness,
            "gamma": self.gamma,
            "pressure_Pa": self.pressure_Pa,
            "emission_current_uA": self.emission_current_uA
        }
        # Add any additional parameters
        data.update(self.additional_params)
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create metadata object from dictionary."""
        metadata = cls(data.get("image_path"))
        metadata.filename = data.get("filename")
        metadata.databar_label = data.get("databar_label")
        metadata.acquisition_time = data.get("acquisition_time")
        metadata.pixels_width = data.get("pixels_width")
        metadata.pixels_height = data.get("pixels_height")
        metadata.pixel_dimension_nm = data.get("pixel_dimension_nm")
        metadata.field_of_view_width = data.get("field_of_view_width")
        metadata.field_of_view_height = data.get("field_of_view_height")
        metadata.magnification = data.get("magnification")
        metadata.mode = data.get("mode")
        metadata.high_voltage_kV = data.get("high_voltage_kV")
        metadata.working_distance_mm = data.get("working_distance_mm")
        metadata.spot_size = data.get("spot_size")
        metadata.dwell_time_ns = data.get("dwell_time_ns")
        metadata.sample_position_x = data.get("sample_position_x")
        metadata.sample_position_y = data.get("sample_position_y")
        metadata.multistage_x = data.get("multistage_x")
        metadata.multistage_y = data.get("multistage_y")
        metadata.beam_shift_x = data.get("beam_shift_x")
        metadata.beam_shift_y = data.get("beam_shift_y")
        metadata.contrast = data.get("contrast")
        metadata.brightness = data.get("brightness")
        metadata.gamma = data.get("gamma")
        metadata.pressure_Pa = data.get("pressure_Pa")
        metadata.emission_current_uA = data.get("emission_current_uA")
        
        # Extract any additional parameters
        for key, value in data.items():
            if key not in metadata.to_dict():
                metadata.additional_params[key] = value
                
        return metadata