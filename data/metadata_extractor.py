"""
Metadata extraction module for SEM images.
"""

import os
import xml.etree.ElementTree as ET
from PIL import Image
from abc import ABC, abstractmethod


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


class MetadataExtractionStrategy(ABC):
    """Base class for metadata extraction strategies."""
    
    @abstractmethod
    def extract(self, image_path):
        """Extract metadata from image."""
        pass


class PhenomXLStrategy(MetadataExtractionStrategy):
    """Strategy for extracting Phenom XL metadata."""
    
    def extract(self, image_path):
        """
        Extracts metadata from Phenom XL SEM TIFF images.
        
        Args:
            image_path (str): Path to the TIFF file.
            
        Returns:
            ImageMetadata: Extracted metadata object.
        """
        metadata = ImageMetadata(image_path)
        
        try:
            # Open the TIFF file using Pillow
            with Image.open(image_path) as img:
                # TIFF images may store metadata in tag 34683
                xml_data = img.tag_v2.get(34683)
                
                if not xml_data:
                    raise ValueError(f"No XML metadata found in the TIFF file: {image_path}")
                
                # Convert bytes to string if necessary
                if isinstance(xml_data, bytes):
                    xml_data = xml_data.decode("utf-8")

                # Parse the XML
                root = ET.fromstring(xml_data)

                # Extract basic dimensions
                width_pix = int(root.find("cropHint/right").text) 
                height_pix = int(root.find("cropHint/bottom").text)
                pixel_dim_nm = float(root.find("pixelWidth").text)
                field_of_view_width = pixel_dim_nm * width_pix / 1000  # Convert to μm
                field_of_view_height = pixel_dim_nm * height_pix / 1000  # Convert to μm
                magnification = int(127000 / field_of_view_width)  # Calculate magnification
                
                # Extract stage position information
                multi_stage = root.find("multiStage")
                multi_stage_x = None
                multi_stage_y = None
                if multi_stage:
                    for axis in multi_stage.findall("axis"):
                        if axis.get("id") == "X":
                            multi_stage_x = float(axis.text)
                        elif axis.get("id") == "Y":
                            multi_stage_y = float(axis.text)

                # Extract beam shift information
                beam_shift = root.find("acquisition/scan/beamShift")
                beam_shift_x = None
                beam_shift_y = None
                if beam_shift is not None:
                    beam_shift_x = float(beam_shift.find("x").text)
                    beam_shift_y = float(beam_shift.find("y").text)

                # Fill the metadata object with extracted values
                metadata.databar_label = root.findtext("databarLabel")
                metadata.acquisition_time = root.findtext("time")
                metadata.pixels_width = width_pix
                metadata.pixels_height = height_pix
                metadata.pixel_dimension_nm = pixel_dim_nm
                metadata.field_of_view_width = field_of_view_width
                metadata.field_of_view_height = field_of_view_height
                metadata.magnification = magnification
                metadata.mode = root.find("acquisition/scan/detector").text
                metadata.high_voltage_kV = abs(float(root.find("acquisition/scan/highVoltage").text))
                metadata.working_distance_mm = float(root.find("workingDistance").text)
                metadata.spot_size = float(root.find("acquisition/scan/spotSize").text)
                metadata.dwell_time_ns = int(root.find("acquisition/scan/dwellTime").text)
                metadata.sample_position_x = float(root.find("samplePosition/x").text)
                metadata.sample_position_y = float(root.find("samplePosition/y").text)
                metadata.multistage_x = multi_stage_x
                metadata.multistage_y = multi_stage_y
                metadata.beam_shift_x = beam_shift_x
                metadata.beam_shift_y = beam_shift_y
                metadata.contrast = float(root.find("appliedContrast").text)
                metadata.brightness = float(root.find("appliedBrightness").text)
                metadata.gamma = float(root.find("appliedGamma").text)
                metadata.pressure_Pa = float(root.find("samplePressureEstimate").text)
                metadata.emission_current_uA = float(root.find("acquisition/scan/emissionCurrent").text)
                
                # Extract instrument information
                instrument = root.find("instrument")
                if instrument is not None:
                    metadata.additional_params["instrument_type"] = instrument.findtext("type")
                    metadata.additional_params["software_version"] = instrument.findtext("softwareVersion")
                    metadata.additional_params["instrument_id"] = instrument.findtext("uniqueID")
                    
                return metadata
                
        except Exception as e:
            # Log the error in production code
            print(f"Error extracting metadata from {image_path}: {str(e)}")
            return metadata


class MetadataExtractor:
    """Uses strategies to extract metadata from images."""
    
    def __init__(self):
        """Initialize extractor with available strategies."""
        self.strategies = {
            "phenomxl": PhenomXLStrategy(),
            # Add other strategies as needed
        }
    
    def extract_metadata(self, image_path, device_type=None):
        """
        Extract metadata using appropriate strategy.
        
        Args:
            image_path (str): Path to the image file.
            device_type (str, optional): Type of device to use for extraction.
                If None, will attempt to auto-detect.
                
        Returns:
            ImageMetadata: Extracted metadata object.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        if not device_type:
            # Auto-detect device type from image
            device_type = self._detect_device_type(image_path)
            
        if device_type in self.strategies:
            return self.strategies[device_type].extract(image_path)
        else:
            raise ValueError(f"Unsupported device type: {device_type}")
            
    def _detect_device_type(self, image_path):
        """
        Detect device type from image characteristics.
        
        Args:
            image_path (str): Path to the image file.
            
        Returns:
            str: Detected device type.
        """
        # Default to PhenomXL for now
        # In the future, implement more sophisticated detection
        return "phenomxl"
    
    def add_strategy(self, name, strategy):
        """
        Add a new metadata extraction strategy.
        
        Args:
            name (str): Name for the strategy.
            strategy (MetadataExtractionStrategy): Strategy implementation.
        """
        if not isinstance(strategy, MetadataExtractionStrategy):
            raise TypeError("Strategy must implement MetadataExtractionStrategy interface")
        self.strategies[name] = strategy


# Example usage (to be removed in final version):
if __name__ == "__main__":
    # Test the extractor on a sample image
    extractor = MetadataExtractor()
    metadata = extractor.extract_metadata("path/to/sample/image.tiff")
    print(metadata.to_dict())
