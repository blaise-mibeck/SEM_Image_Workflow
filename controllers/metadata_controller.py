"""
Controller for metadata extraction and management.
"""

import os
from typing import Dict, List, Optional, Any

from models.image_metadata import ImageMetadata
from data.metadata_extractor import MetadataExtractor


class MetadataController:
    """
    Controller for handling metadata extraction and caching.
    Serves as an interface between the UI and the metadata extraction logic.
    """
    
    def __init__(self):
        """Initialize the metadata controller."""
        self.metadata_extractor = MetadataExtractor()
        self.metadata_cache: Dict[str, ImageMetadata] = {}
    
    def extract_metadata(self, image_path: str, force_reload: bool = False) -> Optional[ImageMetadata]:
        """
        Extract metadata from an image file.
        
        Args:
            image_path (str): Path to the image file
            force_reload (bool): Whether to force extraction even if already in cache
            
        Returns:
            Optional[ImageMetadata]: Extracted metadata or None if extraction fails
        """
        # Check cache first if not forcing reload
        if not force_reload and image_path in self.metadata_cache:
            return self.metadata_cache[image_path]
        
        # Check if file exists
        if not os.path.exists(image_path):
            return None
        
        try:
            # Extract metadata using the extractor
            metadata = self.metadata_extractor.extract_metadata(image_path)
            
            # Cache the result
            self.metadata_cache[image_path] = metadata
            
            return metadata
        except Exception as e:
            print(f"Error extracting metadata from {image_path}: {str(e)}")
            return None
    
    def batch_extract_metadata(self, image_paths: List[str], 
                               callback=None) -> Dict[str, ImageMetadata]:
        """
        Extract metadata from multiple images.
        
        Args:
            image_paths (List[str]): List of image file paths
            callback: Optional callback function to report progress
            
        Returns:
            Dict[str, ImageMetadata]: Dictionary mapping file paths to metadata
        """
        results = {}
        total = len(image_paths)
        
        for i, path in enumerate(image_paths):
            # Extract metadata
            metadata = self.extract_metadata(path)
            
            if metadata:
                results[path] = metadata
            
            # Report progress if callback provided
            if callback and callable(callback):
                callback(i + 1, total)
        
        return results
    
    def clear_cache(self) -> None:
        """Clear the metadata cache."""
        self.metadata_cache.clear()
    
    def get_cached_metadata(self, image_path: str) -> Optional[ImageMetadata]:
        """
        Get metadata from cache if available.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Optional[ImageMetadata]: Cached metadata or None if not in cache
        """
        return self.metadata_cache.get(image_path)
    
    def is_metadata_valid(self, metadata: Optional[ImageMetadata]) -> bool:
        """
        Check if metadata is valid for workflow processing.
        
        Args:
            metadata (Optional[ImageMetadata]): Metadata to check
            
        Returns:
            bool: True if metadata is valid for workflows
        """
        return metadata is not None and metadata.is_valid()
    
    def save_metadata_to_file(self, image_paths: List[str], output_path: str) -> bool:
        """
        Save metadata for multiple images to a JSON file.
        
        Args:
            image_paths (List[str]): List of image file paths
            output_path (str): Path to save the metadata file
            
        Returns:
            bool: True if saving was successful
        """
        import json
        
        try:
            # Extract metadata for all images
            metadata_dict = {}
            for path in image_paths:
                metadata = self.extract_metadata(path)
                if metadata:
                    metadata_dict[path] = metadata.to_dict()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save to file
            with open(output_path, 'w') as f:
                json.dump(metadata_dict, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving metadata to file: {str(e)}")
            return False
    
    def load_metadata_from_file(self, file_path: str) -> bool:
        """
        Load metadata from a previously saved JSON file into the cache.
        
        Args:
            file_path (str): Path to the metadata file
            
        Returns:
            bool: True if loading was successful
        """
        import json
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False
                
            # Load from file
            with open(file_path, 'r') as f:
                metadata_dict = json.load(f)
            
            # Reconstruct metadata objects and add to cache
            for path, data in metadata_dict.items():
                metadata = ImageMetadata.from_dict(data)
                self.metadata_cache[path] = metadata
                
            return True
        except Exception as e:
            print(f"Error loading metadata from file: {str(e)}")
            return False


# Example usage (to be removed in final version):
if __name__ == "__main__":
    controller = MetadataController()
    
    # Extract metadata from a single image
    image_path = "path/to/image.tiff"
    metadata = controller.extract_metadata(image_path)
    
    if metadata:
        print(f"Extracted metadata from {image_path}")
        print(f"Mode: {metadata.mode}")
        print(f"Magnification: {metadata.magnification}x")