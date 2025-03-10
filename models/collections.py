"""
Collection models for organizing images within workflows.
"""

import os
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod


class Collection(ABC):
    """Base class for image collections in various workflows."""
    
    def __init__(self, name: str, workflow_type: str):
        self.name = name
        self.workflow_type = workflow_type
        self.images: List[str] = []  # List of image paths in collection
        self.created_by = None
        self.creation_date = datetime.datetime.now().isoformat()
    
    def add_image(self, image_path: str) -> None:
        """Add image to collection."""
        if os.path.exists(image_path) and image_path not in self.images:
            self.images.append(image_path)
    
    def remove_image(self, image_path: str) -> None:
        """Remove image from collection."""
        if image_path in self.images:
            self.images.remove(image_path)
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if collection satisfies workflow requirements."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary for storage."""
        return {
            "name": self.name,
            "workflow_type": self.workflow_type,
            "images": self.images,
            "created_by": self.created_by,
            "creation_date": self.creation_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Collection':
        """Create collection from dictionary."""
        raise NotImplementedError("Must be implemented by subclass")


class MagGridCollection(Collection):
    """Collection for MagGrid workflow."""
    
    def __init__(self, name: str):
        super().__init__(name, "MagGrid")
        self.magnification_levels: Dict[int, List[str]] = {}  # Dict mapping magnification to images
        self.hierarchy: Dict[str, List[str]] = {}  # Dict mapping low mag image to list of higher mag images
    
    def add_image(self, image_path: str, magnification: int) -> None:
        """
        Add image to collection with its magnification.
        
        Args:
            image_path (str): Path to the image file
            magnification (int): Magnification level of the image
        """
        super().add_image(image_path)
        
        # Add to magnification levels
        if magnification not in self.magnification_levels:
            self.magnification_levels[magnification] = []
        
        if image_path not in self.magnification_levels[magnification]:
            self.magnification_levels[magnification].append(image_path)
    
    def remove_image(self, image_path: str) -> None:
        """
        Remove image from collection.
        
        Args:
            image_path (str): Path to the image file
        """
        super().remove_image(image_path)
        
        # Remove from magnification levels
        for mag, images in list(self.magnification_levels.items()):
            if image_path in images:
                images.remove(image_path)
                if not images:  # If no images left at this magnification
                    del self.magnification_levels[mag]
                break
        
        # Remove from hierarchy
        if image_path in self.hierarchy:
            del self.hierarchy[image_path]
        
        # Remove as child in hierarchy
        for parent, children in list(self.hierarchy.items()):
            if image_path in children:
                children.remove(image_path)
    
    def set_hierarchy(self, low_mag_image: str, high_mag_images: List[str]) -> None:
        """
        Set hierarchical relationship between images.
        
        Args:
            low_mag_image (str): Path to lower magnification image
            high_mag_images (List[str]): List of paths to higher magnification images
        """
        self.hierarchy[low_mag_image] = high_mag_images
    
    def get_sorted_magnifications(self) -> List[int]:
        """
        Get magnification levels sorted from lowest to highest.
        
        Returns:
            List[int]: Sorted magnification levels
        """
        return sorted(self.magnification_levels.keys())
    
    def get_images_at_magnification(self, magnification: int) -> List[str]:
        """
        Get all images at a specific magnification.
        
        Args:
            magnification (int): Magnification level
            
        Returns:
            List[str]: List of image paths at the specified magnification
        """
        return self.magnification_levels.get(magnification, [])
    
    def check_image_containment(self, low_mag_image: str, high_mag_image: str,
                                low_mag_metadata: Any, high_mag_metadata: Any) -> bool:
        """
        Check if high mag image is contained within low mag image.
        
        Args:
            low_mag_image (str): Path to lower magnification image
            high_mag_image (str): Path to higher magnification image
            low_mag_metadata (Any): Metadata for lower magnification image
            high_mag_metadata (Any): Metadata for higher magnification image
            
        Returns:
            bool: True if high mag image is contained within low mag image
        """
        # For proper implementation, we need to calculate if the high mag field of view
        # is fully contained in the low mag field of view based on stage position and FOV dimensions
        
        # Get positions and field of view dimensions
        low_x = low_mag_metadata.sample_position_x
        low_y = low_mag_metadata.sample_position_y
        low_width = low_mag_metadata.field_of_view_width
        low_height = low_mag_metadata.field_of_view_height
        
        high_x = high_mag_metadata.sample_position_x
        high_y = high_mag_metadata.sample_position_y
        high_width = high_mag_metadata.field_of_view_width
        high_height = high_mag_metadata.field_of_view_height
        
        # Calculate boundaries of the low mag image
        low_left = low_x - (low_width / 2)
        low_right = low_x + (low_width / 2)
        low_top = low_y - (low_height / 2)
        low_bottom = low_y + (low_height / 2)
        
        # Calculate boundaries of the high mag image
        high_left = high_x - (high_width / 2)
        high_right = high_x + (high_width / 2)
        high_top = high_y - (high_height / 2)
        high_bottom = high_y + (high_height / 2)
        
        # Check if high mag image is completely contained within low mag image
        return (
            high_left >= low_left and
            high_right <= low_right and
            high_top >= low_top and
            high_bottom <= low_bottom
        )
    
    def calculate_bounding_box(self, low_mag_metadata: Any, high_mag_metadata: Any) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box coordinates of high mag image within low mag image.
        
        Args:
            low_mag_metadata (Any): Metadata for lower magnification image
            high_mag_metadata (Any): Metadata for higher magnification image
            
        Returns:
            Tuple[float, float, float, float]: (x1, y1, x2, y2) coordinates of bounding box
            normalized to [0,1] range where (0,0) is top-left and (1,1) is bottom-right
        """
        # Get positions and field of view dimensions
        low_x = low_mag_metadata.sample_position_x
        low_y = low_mag_metadata.sample_position_y
        low_width = low_mag_metadata.field_of_view_width
        low_height = low_mag_metadata.field_of_view_height
        
        high_x = high_mag_metadata.sample_position_x
        high_y = high_mag_metadata.sample_position_y
        high_width = high_mag_metadata.field_of_view_width
        high_height = high_mag_metadata.field_of_view_height
        
        # Calculate boundaries of the low mag image
        low_left = low_x - (low_width / 2)
        low_right = low_x + (low_width / 2)
        low_top = low_y - (low_height / 2)
        low_bottom = low_y + (low_height / 2)
        
        # Calculate boundaries of the high mag image
        high_left = high_x - (high_width / 2)
        high_right = high_x + (high_width / 2)
        high_top = high_y - (high_height / 2)
        high_bottom = high_y + (high_height / 2)
        
        # Calculate normalized coordinates for bounding box
        # where (0,0) is top-left and (1,1) is bottom-right of low mag image
        x1 = (high_left - low_left) / low_width
        y1 = (high_top - low_top) / low_height
        x2 = (high_right - low_left) / low_width
        y2 = (high_bottom - low_top) / low_height
        
        # Ensure coordinates are within [0,1] range
        x1 = max(0, min(1, x1))
        y1 = max(0, min(1, y1))
        x2 = max(0, min(1, x2))
        y2 = max(0, min(1, y2))
        
        return (x1, y1, x2, y2)
    
    def is_valid(self) -> bool:
        """
        Check if collection satisfies MagGrid workflow requirements.
        
        Returns:
            bool: True if collection is valid
        """
        # Need at least 2 images
        if len(self.images) < 2:
            return False
            
        # Need at least 2 magnification levels
        if len(self.magnification_levels) < 2:
            return False
            
        # Need at least one hierarchical relationship
        if not self.hierarchy:
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert collection to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of collection
        """
        base_dict = super().to_dict()
        
        # Add MagGrid specific attributes
        mag_levels_dict = {}
        for mag, images in self.magnification_levels.items():
            mag_levels_dict[str(mag)] = images
            
        base_dict.update({
            "magnification_levels": mag_levels_dict,
            "hierarchy": self.hierarchy
        })
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MagGridCollection':
        """
        Create collection from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of collection
            
        Returns:
            MagGridCollection: Reconstructed collection
        """
        collection = cls(data.get("name"))
        collection.images = data.get("images", [])
        collection.created_by = data.get("created_by")
        collection.creation_date = data.get("creation_date")
        
        # Reconstruct magnification levels
        mag_levels_dict = data.get("magnification_levels", {})
        for mag_str, images in mag_levels_dict.items():
            collection.magnification_levels[int(mag_str)] = images
            
        # Reconstruct hierarchy
        collection.hierarchy = data.get("hierarchy", {})
        
        return collection


class ModeGridCollection(Collection):
    """Collection for ModeGrid workflow."""
    
    def __init__(self, name: str):
        super().__init__(name, "ModeGrid")
        self.mode_map: Dict[str, List[str]] = {}  # Dict mapping modes to images
        self.magnification: Optional[int] = None  # All images should have approximately the same magnification
    
    def add_image(self, image_path: str, mode: str, magnification: int) -> None:
        """
        Add image to collection with its mode and magnification.
        
        Args:
            image_path (str): Path to the image file
            mode (str): Imaging mode (SED, BSD, Topo, etc.)
            magnification (int): Magnification level of the image
        """
        super().add_image(image_path)
        
        # Set magnification if not set
        if self.magnification is None:
            self.magnification = magnification
        
        # Add to mode map
        if mode not in self.mode_map:
            self.mode_map[mode] = []
        
        if image_path not in self.mode_map[mode]:
            self.mode_map[mode].append(image_path)
    
    def remove_image(self, image_path: str) -> None:
        """
        Remove image from collection.
        
        Args:
            image_path (str): Path to the image file
        """
        super().remove_image(image_path)
        
        # Remove from mode map
        for mode, images in list(self.mode_map.items()):
            if image_path in images:
                images.remove(image_path)
                if not images:  # If no images left for this mode
                    del self.mode_map[mode]
                break
    
    def get_images_by_mode(self, mode: str) -> List[str]:
        """
        Get all images of a specific mode.
        
        Args:
            mode (str): Imaging mode
            
        Returns:
            List[str]: List of image paths with the specified mode
        """
        return self.mode_map.get(mode, [])
    
    def get_available_modes(self) -> List[str]:
        """
        Get list of available modes in the collection.
        
        Returns:
            List[str]: List of modes
        """
        return list(self.mode_map.keys())
    
    def is_valid(self) -> bool:
        """
        Check if collection satisfies ModeGrid workflow requirements.
        
        Returns:
            bool: True if collection is valid
        """
        # Need at least 2 images
        if len(self.images) < 2:
            return False
            
        # Need at least 2 different modes
        if len(self.mode_map) < 2:
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert collection to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of collection
        """
        base_dict = super().to_dict()
        
        # Add ModeGrid specific attributes
        base_dict.update({
            "mode_map": self.mode_map,
            "magnification": self.magnification
        })
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModeGridCollection':
        """
        Create collection from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of collection
            
        Returns:
            ModeGridCollection: Reconstructed collection
        """
        collection = cls(data.get("name"))
        collection.images = data.get("images", [])
        collection.created_by = data.get("created_by")
        collection.creation_date = data.get("creation_date")
        
        # Reconstruct mode map
        collection.mode_map = data.get("mode_map", {})
        collection.magnification = data.get("magnification")
        
        return collection


class CompareGridCollection(Collection):
    """Collection for CompareGrid workflow."""
    
    def __init__(self, name: str):
        super().__init__(name, "CompareGrid")
        self.sample_images: Dict[str, str] = {}  # Dict mapping sample IDs to images
        self.mode: Optional[str] = None  # All images should have the same mode
        self.magnification: Optional[int] = None  # All images should have approximately the same magnification
    
    def add_sample_image(self, sample_id: str, image_path: str, mode: str, magnification: int) -> None:
        """
        Add image for a specific sample.
        
        Args:
            sample_id (str): Sample identifier
            image_path (str): Path to the image file
            mode (str): Imaging mode
            magnification (int): Magnification level
        """
        super().add_image(image_path)
        
        # Set mode and magnification if not set
        if self.mode is None:
            self.mode = mode
        
        if self.magnification is None:
            self.magnification = magnification
        
        # Map sample ID to image
        self.sample_images[sample_id] = image_path
    
    def remove_sample(self, sample_id: str) -> None:
        """
        Remove sample from collection.
        
        Args:
            sample_id (str): Sample identifier
        """
        if sample_id in self.sample_images:
            image_path = self.sample_images[sample_id]
            super().remove_image(image_path)
            del self.sample_images[sample_id]
    
    def get_sample_ids(self) -> List[str]:
        """
        Get list of sample IDs in the collection.
        
        Returns:
            List[str]: List of sample IDs
        """
        return list(self.sample_images.keys())
    
    def get_image_for_sample(self, sample_id: str) -> Optional[str]:
        """
        Get image path for a specific sample.
        
        Args:
            sample_id (str): Sample identifier
            
        Returns:
            Optional[str]: Image path or None if sample not found
        """
        return self.sample_images.get(sample_id)
    
    def is_valid(self) -> bool:
        """
        Check if collection satisfies CompareGrid workflow requirements.
        
        Returns:
            bool: True if collection is valid
        """
        # Need at least 2 samples
        if len(self.sample_images) < 2:
            return False
            
        # All images should exist
        for image_path in self.sample_images.values():
            if not os.path.exists(image_path):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert collection to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of collection
        """
        base_dict = super().to_dict()
        
        # Add CompareGrid specific attributes
        base_dict.update({
            "sample_images": self.sample_images,
            "mode": self.mode,
            "magnification": self.magnification
        })
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompareGridCollection':
        """
        Create collection from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of collection
            
        Returns:
            CompareGridCollection: Reconstructed collection
        """
        collection = cls(data.get("name"))
        collection.images = data.get("images", [])
        collection.created_by = data.get("created_by")
        collection.creation_date = data.get("creation_date")
        
        # Reconstruct sample images map
        collection.sample_images = data.get("sample_images", {})
        collection.mode = data.get("mode")
        collection.magnification = data.get("magnification")
        
        return collection


class MakeGridCollection(Collection):
    """Collection for MakeGrid workflow - flexible manual selection."""
    
    def __init__(self, name: str):
        super().__init__(name, "MakeGrid")
        self.image_order: List[str] = []  # Order of images in the grid
    
    def add_image(self, image_path: str) -> None:
        """
        Add image to collection.
        
        Args:
            image_path (str): Path to the image file
        """
        super().add_image(image_path)
        
        # Add to image order if not already there
        if image_path not in self.image_order:
            self.image_order.append(image_path)
    
    def remove_image(self, image_path: str) -> None:
        """
        Remove image from collection.
        
        Args:
            image_path (str): Path to the image file
        """
        super().remove_image(image_path)
        
        # Remove from image order
        if image_path in self.image_order:
            self.image_order.remove(image_path)
    
    def reorder_images(self, new_order: List[str]) -> None:
        """
        Set new order for images.
        
        Args:
            new_order (List[str]): New image order
            
        Raises:
            ValueError: If new order doesn't match existing images
        """
        # Check if new order contains the same images
        if set(new_order) != set(self.images):
            raise ValueError("New order must contain exactly the same images as the collection")
        
        self.image_order = new_order
    
    def is_valid(self) -> bool:
        """
        Check if collection satisfies MakeGrid workflow requirements.
        
        Returns:
            bool: True if collection is valid
        """
        # Need at least 2 images
        if len(self.images) < 2:
            return False
            
        # All images should exist
        for image_path in self.images:
            if not os.path.exists(image_path):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert collection to dictionary for storage.
        
        Returns:
            Dict[str, Any]: Dictionary representation of collection
        """
        base_dict = super().to_dict()
        
        # Add MakeGrid specific attributes
        base_dict.update({
            "image_order": self.image_order
        })
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MakeGridCollection':
        """
        Create collection from dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary representation of collection
            
        Returns:
            MakeGridCollection: Reconstructed collection
        """
        collection = cls(data.get("name"))
        collection.images = data.get("images", [])
        collection.created_by = data.get("created_by")
        collection.creation_date = data.get("creation_date")
        
        # Reconstruct image order
        collection.image_order = data.get("image_order", [])
        
        return collection


# Example usage (to be removed in final version):
if __name__ == "__main__":
    # Test MagGridCollection
    mag_collection = MagGridCollection("Test MagGrid")
    mag_collection.add_image("path/to/low_mag.tiff", 100)
    mag_collection.add_image("path/to/high_mag.tiff", 500)
    
    # Test ModeGridCollection
    mode_collection = ModeGridCollection("Test ModeGrid")
    mode_collection.add_image("path/to/sed_image.tiff", "SED", 1000)
    mode_collection.add_image("path/to/bsd_image.tiff", "BSD", 1000)
    
    # Test CompareGridCollection
    compare_collection = CompareGridCollection("Test CompareGrid")
    compare_collection.add_sample_image("Sample-001", "path/to/sample1.tiff", "SED", 500)
    compare_collection.add_sample_image("Sample-002", "path/to/sample2.tiff", "SED", 500)
