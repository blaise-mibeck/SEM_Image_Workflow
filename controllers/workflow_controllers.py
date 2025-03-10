"""
Workflow controllers for managing SEM image collections and visualization.
"""

import os
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple, Type
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont
import shutil

# Import models
from models.session import Session
from models.image_metadata import ImageMetadata
from models.collections import (
    Collection, MagGridCollection, ModeGridCollection, 
    CompareGridCollection, MakeGridCollection
)
from data.metadata_extractor import MetadataExtractor


class WorkflowController(ABC):
    """Base class for workflow controllers."""
    
    def __init__(self, session: Session):
        self.session = session
        self.collections: List[Collection] = []
        self.current_collection: Optional[Collection] = None
        self.metadata_cache: Dict[str, ImageMetadata] = {}
        self.metadata_extractor = MetadataExtractor()
        
        # Create workflow folder if it doesn't exist
        self.workflow_folder = os.path.join(session.folder_path, self.get_workflow_type())
        os.makedirs(self.workflow_folder, exist_ok=True)
    
    @abstractmethod
    def get_workflow_type(self) -> str:
        """Get the workflow type string."""
        pass
    
    @abstractmethod
    def get_collection_class(self) -> Type[Collection]:
        """Get the collection class for this workflow."""
        pass
    
    def create_collection(self, name: str) -> Collection:
        """
        Create a new collection.
        
        Args:
            name (str): Name for the collection
            
        Returns:
            Collection: New collection object
        """
        collection = self.get_collection_class()(name)
        self.collections.append(collection)
        self.current_collection = collection
        return collection
    
    def delete_collection(self, collection: Collection) -> None:
        """
        Delete a collection.
        
        Args:
            collection (Collection): Collection to delete
        """
        if collection in self.collections:
            self.collections.remove(collection)
            
            # Update current collection if needed
            if self.current_collection == collection:
                self.current_collection = self.collections[0] if self.collections else None
    
    def load_collections(self) -> None:
        """
        Load collections from session folder.
        
        Creates the workflow folder if it doesn't exist.
        """
        collections_file = os.path.join(self.workflow_folder, "collections.json")
        
        if os.path.exists(collections_file):
            try:
                with open(collections_file, 'r') as f:
                    collections_data = json.load(f)
                
                self.collections = []
                for collection_data in collections_data:
                    if collection_data.get("workflow_type") == self.get_workflow_type():
                        collection = self.get_collection_class().from_dict(collection_data)
                        self.collections.append(collection)
                
                # Set current collection if available
                if self.collections:
                    self.current_collection = self.collections[0]
                    
            except Exception as e:
                print(f"Error loading collections: {str(e)}")
                # Initialize empty collections list
                self.collections = []
                self.current_collection = None
        else:
            # Initialize empty collections list
            self.collections = []
            self.current_collection = None
    
    def save_collections(self) -> None:
        """
        Save collections to session folder.
        """
        collections_file = os.path.join(self.workflow_folder, "collections.json")
        
        try:
            collections_data = [collection.to_dict() for collection in self.collections]
            
            with open(collections_file, 'w') as f:
                json.dump(collections_data, f, indent=4)
                
        except Exception as e:
            print(f"Error saving collections: {str(e)}")
    
    def get_metadata(self, image_path: str) -> Optional[ImageMetadata]:
        """
        Get metadata for an image, using cache if available.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Optional[ImageMetadata]: Metadata object or None if extraction fails
        """
        # Check cache first
        if image_path in self.metadata_cache:
            return self.metadata_cache[image_path]
        
        # Extract metadata
        try:
            metadata = self.metadata_extractor.extract_metadata(image_path)
            self.metadata_cache[image_path] = metadata
            return metadata
        except Exception as e:
            print(f"Error extracting metadata from {image_path}: {str(e)}")
            return None
    
    def calculate_grid_layout(self, image_count: int) -> Tuple[int, int]:
        """
        Calculate appropriate grid layout based on image count.
        
        Args:
            image_count (int): Number of images
            
        Returns:
            Tuple[int, int]: (rows, columns) for grid layout
        """
        if image_count <= 2:
            return (2, 1)  # 2 rows, 1 column
        elif image_count <= 4:
            return (2, 2)  # 2 rows, 2 columns
        else:
            return (3, 2)  # 3 rows, 2 columns for 5-6 images
    
    @abstractmethod
    def build_collections(self) -> List[Collection]:
        """
        Build collections based on workflow criteria.
        
        Returns:
            List[Collection]: List of generated collections
        """
        pass
    
    @abstractmethod
    def validate_collection(self, collection: Collection) -> bool:
        """
        Validate a collection according to workflow rules.
        
        Args:
            collection (Collection): Collection to validate
            
        Returns:
            bool: True if collection is valid
        """
        pass
    
    @abstractmethod
    def create_grid_visualization(self, collection: Collection, layout: Optional[Tuple[int, int]] = None) -> Image.Image:
        """
        Create grid visualization for a collection.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            
        Returns:
            Image.Image: Grid visualization image
        """
        pass
    
    def export_grid(self, collection: Collection, output_path: Optional[str] = None, 
                    layout: Optional[Tuple[int, int]] = None, 
                    annotation_style: Optional[str] = None) -> str:
        """
        Export grid visualization to file.
        
        Args:
            collection (Collection): Collection to export
            output_path (Optional[str]): Path to save the file, or None to auto-generate
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            annotation_style (Optional[str]): Style for annotations (e.g., "solid", "dotted", "none")
            
        Returns:
            str: Path to the exported file
        """
        # Generate visualization
        grid_image = self.create_grid_visualization(collection, layout)
        
        # Generate filename if not provided
        if not output_path:
            # Extract session ID from folder name
            session_id = os.path.basename(self.session.folder_path)
            
            # Get sample ID from session
            sample_id = self.session.sample_id or "unknown"
            
            # Generate filename
            filename = f"{session_id}_{sample_id}_{self.get_workflow_type()}-{len(self.collections)}.png"
            output_path = os.path.join(self.workflow_folder, "exports", filename)
        
        # Ensure export directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save image
        grid_image.save(output_path, "PNG")
        
        # Generate caption
        self.generate_caption(collection, output_path.replace(".png", ".txt"))
        
        return output_path
    
    def generate_caption(self, collection: Collection, output_path: Optional[str] = None) -> str:
        """
        Generate caption for the grid.
        
        Args:
            collection (Collection): Collection to generate caption for
            output_path (Optional[str]): Path to save the caption, or None to auto-generate
            
        Returns:
            str: Generated caption text
        """
        # Generate basic caption text
        caption = f"{self.get_workflow_type()} visualization for {self.session.sample_id or 'unknown sample'}\n\n"
        
        if self.session.sample_type:
            caption += f"Sample Type: {self.session.sample_type}\n"
        
        if self.session.preparation_method:
            caption += f"Preparation Method: {self.session.preparation_method}\n"
        
        # Add workflow-specific caption content
        caption += self._generate_workflow_specific_caption(collection)
        
        # Save caption if output path provided
        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    f.write(caption)
            except Exception as e:
                print(f"Error saving caption: {str(e)}")
        
        return caption
    
    @abstractmethod
    def _generate_workflow_specific_caption(self, collection: Collection) -> str:
        """
        Generate workflow-specific caption content.
        
        Args:
            collection (Collection): Collection to generate caption for
            
        Returns:
            str: Workflow-specific caption text
        """
        pass


class MagGridController(WorkflowController):
    """Controller for MagGrid workflow."""
    
    def get_workflow_type(self) -> str:
        return "MagGrid"
    
    def get_collection_class(self) -> Type[Collection]:
        return MagGridCollection
    
    def build_collections(self) -> List[Collection]:
        """
        Build collections based on MagGrid criteria using spatial containment relationships.
        
        Returns:
            List[Collection]: List of generated collections
        """
        collections = []
        processed_high_mag_images = set()  # Track processed high-mag images
        
        # Get all valid images with metadata
        valid_images = {}
        for image_path in self.session.images:
            metadata = self.get_metadata(image_path)
            if metadata and metadata.is_valid():
                valid_images[image_path] = metadata
        
        # Group images by mode, high voltage, and spot size
        image_groups = {}
        for image_path, metadata in valid_images.items():
            key = (metadata.mode, metadata.high_voltage_kV, metadata.spot_size)
            if key not in image_groups:
                image_groups[key] = []
            image_groups[key].append((image_path, metadata))
        
        collection_index = 1
        
        # For each group (same mode, high voltage, and spot size)
        for (mode, voltage, intensity), images in image_groups.items():
            # Organize images by magnification
            mag_levels = {}
            for img_path, img_metadata in images:
                mag = img_metadata.magnification
                if mag not in mag_levels:
                    mag_levels[mag] = []
                mag_levels[mag].append((img_path, img_metadata))
            
            # Sort magnifications from high to low
            sorted_mags = sorted(mag_levels.keys(), reverse=True)
            
            # If no magnification levels, skip this group
            if not sorted_mags:
                continue
                
            # Start with highest magnification images as seeds for collections
            highest_mag = sorted_mags[0]
            for high_img_path, high_img_metadata in mag_levels[highest_mag]:
                # Skip if already processed
                if high_img_path in processed_high_mag_images:
                    continue
                
                # Create a new collection 
                collection = MagGridCollection(f"MagGrid_{collection_index}")
                collection_index += 1
                
                # Add the high-mag image to the collection
                collection.add_image(high_img_path, high_img_metadata.magnification)
                
                # Mark as processed
                processed_high_mag_images.add(high_img_path)
                
                # Build the containment chain for this high-mag image
                current_img_path = high_img_path
                current_img_metadata = high_img_metadata
                
                # For each lower magnification level
                for mag in sorted_mags[1:]:  # Skip the highest mag (already added)
                    # Find best containing image at this magnification
                    best_container = self._find_best_container(current_img_metadata, mag_levels[mag])
                    
                    if best_container:
                        container_path, container_metadata = best_container
                        
                        # Add to collection
                        collection.add_image(container_path, container_metadata.magnification)
                        
                        # Set hierarchy relationship
                        collection.set_hierarchy(container_path, [current_img_path])
                        
                        # Update current image for next level
                        current_img_path = container_path
                        current_img_metadata = container_metadata
                    else:
                        # No container found at this magnification level, break the chain
                        break
                
                # Only add collections with at least 2 images (a hierarchy)
                if len(collection.images) >= 2:
                    collections.append(collection)
        
        return collections
    
    def _find_best_container(self, target_metadata, candidate_images):
        """
        Find the best containing image for a target image.
        
        Args:
            target_metadata: Metadata for the target (higher magnification) image
            candidate_images: List of (path, metadata) tuples for potential container images
            
        Returns:
            Tuple of (path, metadata) for the best container, or None if none found
        """
        valid_containers = []
        
        for candidate_path, candidate_metadata in candidate_images:
            # Check if candidate contains target with 10% margin
            is_contained = self._check_strict_containment(candidate_metadata, target_metadata)
            
            if is_contained:
                valid_containers.append((candidate_path, candidate_metadata, 
                                         self._calculate_containment_score(candidate_metadata, target_metadata)))
        
        if not valid_containers:
            return None
            
        # Choose the container with the best score (lower is better)
        best_container = min(valid_containers, key=lambda x: x[2])
        return best_container[0], best_container[1]
    
    def _calculate_containment_score(self, container_metadata, contained_metadata):
        """
        Calculate a score for how well a container contains an image.
        Lower score is better - represents a tighter, more centered containment.
        
        Args:
            container_metadata: Metadata for the container (lower magnification) image
            contained_metadata: Metadata for the contained (higher magnification) image
            
        Returns:
            float: Containment score (lower is better)
        """
        # Calculate center offset
        container_center_x = container_metadata.sample_position_x
        container_center_y = container_metadata.sample_position_y
        contained_center_x = contained_metadata.sample_position_x
        contained_center_y = contained_metadata.sample_position_y
        
        # Calculate normalized offset from center (0-1 range where 0 is perfect centering)
        offset_x = abs(container_center_x - contained_center_x) / (container_metadata.field_of_view_width / 2)
        offset_y = abs(container_center_y - contained_center_y) / (container_metadata.field_of_view_height / 2)
        
        # Calculate size ratio (how much of the container is used by the contained image)
        area_container = container_metadata.field_of_view_width * container_metadata.field_of_view_height
        area_contained = contained_metadata.field_of_view_width * contained_metadata.field_of_view_height
        size_ratio = area_contained / area_container
        
        # Combined score: balance between centering and size efficiency
        # Weighted to prefer more centered containment
        centering_score = (offset_x + offset_y) * 0.7
        size_score = (1 - size_ratio) * 0.3  # Smaller ratio (bigger difference) increases score
        
        return centering_score + size_score
    
    def _check_strict_containment(self, low_metadata: Any, high_metadata: Any) -> bool:
        """
        Check if high mag image is contained within low mag image.
        
        Args:
            low_metadata (Any): Metadata for lower magnification image
            high_metadata (Any): Metadata for higher magnification image
            
        Returns:
            bool: True if high mag image is definitely contained within low mag image
        """
        # Get positions and field of view dimensions
        low_x = low_metadata.sample_position_x
        low_y = low_metadata.sample_position_y
        low_width = low_metadata.field_of_view_width
        low_height = low_metadata.field_of_view_height
        
        high_x = high_metadata.sample_position_x
        high_y = high_metadata.sample_position_y
        high_width = high_metadata.field_of_view_width
        high_height = high_metadata.field_of_view_height
        
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
        
        # Containment check with 10% margin
        margin_x = low_width * 0.1
        margin_y = low_height * 0.1
        
        strict_containment = (
            high_left >= (low_left + margin_x) and
            high_right <= (low_right - margin_x) and
            high_top >= (low_top + margin_y) and
            high_bottom <= (low_bottom - margin_y)
        )
        
        # Additional check: make sure there's a significant difference in magnification
        mag_ratio = high_metadata.magnification / low_metadata.magnification
        significant_mag_difference = mag_ratio >= 1.5  # At least 50% higher magnification
        
        return strict_containment and significant_mag_difference
    
    def validate_collection(self, collection: Collection) -> bool:
        """
        Validate a collection according to MagGrid workflow rules.
        
        Args:
            collection (Collection): Collection to validate
            
        Returns:
            bool: True if collection is valid
        """
        if not isinstance(collection, MagGridCollection):
            return False
        
        return collection.is_valid()
    
    def create_grid_visualization(self, collection: Collection, layout: Optional[Tuple[int, int]] = None,
                                annotation_style: str = "solid", preserve_resolution: bool = True) -> Image.Image:
        """
        Create grid visualization for a MagGrid collection.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            annotation_style (str): Style for annotations ("solid", "dotted", "none")
            preserve_resolution (bool): Whether to preserve original image resolution
            
        Returns:
            Image.Image: Grid visualization image
        """
        if not isinstance(collection, MagGridCollection):
            raise ValueError("Collection must be a MagGridCollection")
        
        # Get sorted magnifications
        magnifications = collection.get_sorted_magnifications()
        
        # Determine grid layout
        if layout:
            rows, cols = layout
        else:
            rows, cols = self.calculate_grid_layout(len(magnifications))
        
        # Load images and calculate max dimensions
        images = []
        
        for mag in magnifications[:rows*cols]:  # Limit to grid capacity
            # Get first image at this magnification
            image_paths = collection.get_images_at_magnification(mag)
            if not image_paths:
                continue
                
            image_path = image_paths[0]
            img = Image.open(image_path)
            images.append((image_path, img, mag))
        
        # If preserve_resolution is True, use original image dimensions
        if preserve_resolution:
            # Use original dimensions
            grid_images = []
            for image_path, img, mag in images:
                grid_images.append((image_path, img.copy(), mag))
        else:
            # Calculate max dimensions while preserving aspect ratio
            target_width = max(img.width for _, img, _ in images)
            
            # Resize images preserving aspect ratio
            grid_images = []
            for image_path, img, mag in images:
                aspect_ratio = img.height / img.width
                new_height = int(target_width * aspect_ratio)
                resized_img = img.resize((target_width, new_height), Image.LANCZOS)
                grid_images.append((image_path, resized_img, mag))
        
        # Padding between images
        padding = 4
        
        # Calculate grid dimensions
        # For each row, calculate the maximum width and sum of heights
        grid_layout = []
        for r in range(rows):
            row_images = []
            for c in range(cols):
                idx = r * cols + c
                if idx < len(grid_images):
                    row_images.append(grid_images[idx])
            if row_images:
                grid_layout.append(row_images)
        
        # Calculate total width and height
        row_heights = [max(img.height for _, img, _ in row) for row in grid_layout]
        col_widths = []
        for c in range(cols):
            width = 0
            for r in range(rows):
                if r < len(grid_layout) and c < len(grid_layout[r]):
                    width = max(width, grid_layout[r][c][1].width)
            col_widths.append(width)
        
        total_width = sum(col_widths) + (cols - 1) * padding
        total_height = sum(row_heights) + (rows - 1) * padding
        
        # Create grid image
        grid_img = Image.new('RGB', (total_width, total_height), (255, 255, 255))
        draw = ImageDraw.Draw(grid_img)
        
        # Define annotation colors
        colors = [(255, 0, 0), (0, 255, 0), (0, 255, 255), (255, 0, 255), (255, 255, 0)]
        
        # Place images in grid
        y_offset = 0
        for r, row in enumerate(grid_layout):
            x_offset = 0
            for c, (image_path, img, mag) in enumerate(row):
                # Center the image in its cell
                cell_width = col_widths[c]
                cell_height = row_heights[r]
                x_pos = x_offset + (cell_width - img.width) // 2
                y_pos = y_offset + (cell_height - img.height) // 2
                
                # Paste image into grid
                grid_img.paste(img, (x_pos, y_pos))
                
                # Draw annotations if enabled
                if annotation_style != "none" and isinstance(collection, MagGridCollection):
                    idx = r * cols + c
                    # Draw border for current image (except for lowest magnification)
                    if idx > 0 and idx < len(grid_images):
                        color = colors[(idx - 1) % len(colors)]
                        
                        if annotation_style == "solid":
                            draw.rectangle([x_pos, y_pos, x_pos + img.width - 1, y_pos + img.height - 1], 
                                        outline=color, width=2)
                        else:  # dotted
                            # Draw dotted rectangle
                            for j in range(0, img.width, 6):
                                draw.line([x_pos + j, y_pos, x_pos + min(j + 3, img.width), y_pos], fill=color, width=2)
                                draw.line([x_pos + j, y_pos + img.height - 1, x_pos + min(j + 3, img.width), y_pos + img.height - 1], fill=color, width=2)
                            for j in range(0, img.height, 6):
                                draw.line([x_pos, y_pos + j, x_pos, y_pos + min(j + 3, img.height)], fill=color, width=2)
                                draw.line([x_pos + img.width - 1, y_pos + j, x_pos + img.width - 1, y_pos + min(j + 3, img.height)], fill=color, width=2)
                    
                    # Find the next higher magnification image (if any)
                    if idx < len(grid_images) - 1:
                        # Get next higher magnification image
                        next_image_path = grid_images[idx + 1][0]
                        
                        # Find if this is a hierarchical relationship
                        if next_image_path in collection.hierarchy.get(image_path, []):
                            # Get metadata for both images
                            current_metadata = self.get_metadata(image_path)
                            next_metadata = self.get_metadata(next_image_path)
                            
                            if current_metadata and next_metadata:
                                # Calculate bounding box coordinates using spatial data
                                bbox = self._calculate_bounding_box(current_metadata, next_metadata)
                                
                                # Convert normalized coordinates to pixel coordinates
                                x1 = x_pos + int(bbox[0] * img.width)
                                y1 = y_pos + int(bbox[1] * img.height)
                                x2 = x_pos + int(bbox[2] * img.width)
                                y2 = y_pos + int(bbox[3] * img.height)
                                
                                color = colors[idx % len(colors)]
                                
                                if annotation_style == "solid":
                                    draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                                else:  # dotted
                                    # Draw dotted rectangle
                                    box_width = x2 - x1
                                    box_height = y2 - y1
                                    for j in range(0, box_width, 6):
                                        draw.line([x1 + j, y1, x1 + min(j + 3, box_width), y1], fill=color, width=2)
                                        draw.line([x1 + j, y2, x1 + min(j + 3, box_width), y2], fill=color, width=2)
                                    for j in range(0, box_height, 6):
                                        draw.line([x1, y1 + j, x1, y1 + min(j + 3, box_height)], fill=color, width=2)
                                        draw.line([x2, y1 + j, x2, y1 + min(j + 3, box_height)], fill=color, width=2)
                
                x_offset += cell_width + padding
            
            y_offset += row_heights[r] + padding
        
        return grid_img
    
    def _calculate_bounding_box(self, low_metadata: Any, high_metadata: Any) -> Tuple[float, float, float, float]:
        """
        Calculate accurate bounding box coordinates for high mag image within low mag image.
        Converts microscope coordinates to normalized image coordinates.
        
        Args:
            low_metadata (Any): Metadata for lower magnification image
            high_metadata (Any): Metadata for higher magnification image
            
        Returns:
            Tuple[float, float, float, float]: (x1, y1, x2, y2) coordinates of bounding box
            normalized to [0,1] range where (0,0) is top-left and (1,1) is bottom-right
        """
        # Get positions and field of view dimensions (in microscope coordinates, μm)
        low_center_x = low_metadata.sample_position_x
        low_center_y = low_metadata.sample_position_y
        low_width = low_metadata.field_of_view_width
        low_height = low_metadata.field_of_view_height
        
        high_center_x = high_metadata.sample_position_x
        high_center_y = high_metadata.sample_position_y
        high_width = high_metadata.field_of_view_width
        high_height = high_metadata.field_of_view_height
        
        # Calculate boundaries of the low mag image in microscope coordinates
        low_left = low_center_x - (low_width / 2)
        low_top = low_center_y - (low_height / 2)
        
        # Calculate boundaries of the high mag image in microscope coordinates
        high_left = high_center_x - (high_width / 2)
        high_right = high_center_x + (high_width / 2)
        high_top = high_center_y - (high_height / 2)
        high_bottom = high_center_y + (high_height / 2)
        
        # Convert microscope coordinates to normalized image coordinates (0-1)
        # where (0,0) is the top-left of the low mag image and (1,1) is the bottom-right
        x1 = (high_left - low_left) / low_width
        y1 = (high_top - low_top) / low_height
        x2 = (high_right - low_left) / low_width
        y2 = (high_bottom - low_top) / low_height
        
        # Ensure coordinates are within [0,1] range
        # This handles edge cases where the high mag image might extend beyond the low mag image
        x1 = max(0, min(1, x1))
        y1 = max(0, min(1, y1))
        x2 = max(0, min(1, x2))
        y2 = max(0, min(1, y2))
        
        return (x1, y1, x2, y2)
    
    def _generate_workflow_specific_caption(self, collection: Collection) -> str:
        """
        Generate MagGrid-specific caption content.
        
        Args:
            collection (Collection): Collection to generate caption for
            
        Returns:
            str: MagGrid-specific caption text
        """
        if not isinstance(collection, MagGridCollection):
            return ""
        
        caption = "\nMagGrid Visualization Details:\n"
        
        # Add information about magnification levels
        magnifications = collection.get_sorted_magnifications()
        caption += f"Showing {len(magnifications)} magnification levels: "
        caption += ", ".join([f"{mag}x" for mag in magnifications])
        caption += "\n"
        
        # Add information about imaging mode
        if collection.images:
            first_image = collection.images[0]
            metadata = self.get_metadata(first_image)
            if metadata:
                caption += f"Imaging mode: {metadata.mode}\n"
                caption += f"High voltage: {metadata.high_voltage_kV} kV\n"
                caption += f"Spot size: {metadata.spot_size}\n"
        
        return caption
    
class ModeGridController(WorkflowController):
    """Controller for ModeGrid workflow."""
    
    def get_workflow_type(self) -> str:
        return "ModeGrid"
    
    def get_collection_class(self) -> Type[Collection]:
        return ModeGridCollection
    
    def build_collections(self) -> List[Collection]:
        """
        Build collections based on ModeGrid criteria.
        
        Returns:
            List[Collection]: List of generated collections
        """
        collections = []
        processed_images = set()
        
        # Get all valid images with metadata
        valid_images = {}
        for image_path in self.session.images:
            metadata = self.get_metadata(image_path)
            if metadata and metadata.is_valid():
                valid_images[image_path] = metadata
        
        # Group images by location and magnification
        # Two images are considered to be of the same location if they are within 5% of FOV distance
        location_groups = []
        
        for image_path, metadata in valid_images.items():
            if image_path in processed_images:
                continue
                
            # Start a new location group
            group = [(image_path, metadata)]
            processed_images.add(image_path)
            
            # Find other images at the same location
            for other_path, other_metadata in valid_images.items():
                if other_path not in processed_images:
                    # Check if magnifications are similar (within 10%)
                    mag_ratio = metadata.magnification / other_metadata.magnification
                    if 0.9 < mag_ratio < 1.1:
                        # Check if positions are close
                        distance = ((metadata.sample_position_x - other_metadata.sample_position_x) ** 2 + 
                                   (metadata.sample_position_y - other_metadata.sample_position_y) ** 2) ** 0.5
                        
                        # Consider close if within 5% of field of view width
                        if distance < 0.05 * metadata.field_of_view_width:
                            group.append((other_path, other_metadata))
                            processed_images.add(other_path)
            
            location_groups.append(group)
        
        # Create collections for each location group with multiple modes
        collection_index = 1
        for group in location_groups:
            # Check if group has multiple modes
            modes = set(item[1].mode for item in group)
            if len(modes) >= 2:
                # Create collection
                collection = ModeGridCollection(f"ModeGrid_{collection_index}")
                
                # Add images to collection
                for image_path, metadata in group:
                    collection.add_image(image_path, metadata.mode, metadata.magnification)
                
                collections.append(collection)
                collection_index += 1
        
        return collections
    
    def validate_collection(self, collection: Collection) -> bool:
        """
        Validate a collection according to ModeGrid workflow rules.
        
        Args:
            collection (Collection): Collection to validate
            
        Returns:
            bool: True if collection is valid
        """
        if not isinstance(collection, ModeGridCollection):
            return False
        
        return collection.is_valid()
    
    def create_grid_visualization(self, collection: Collection, layout: Optional[Tuple[int, int]] = None) -> Image.Image:
        """
        Create grid visualization for a ModeGrid collection.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            
        Returns:
            Image.Image: Grid visualization image
        """
        if not isinstance(collection, ModeGridCollection):
            raise ValueError("Collection must be a ModeGridCollection")
        
        # Get available modes
        modes = collection.get_available_modes()
        
        # Determine grid layout
        if layout:
            rows, cols = layout
        else:
            rows, cols = self.calculate_grid_layout(len(modes))
        
        # Load images and calculate max dimensions
        images = []
        max_width = 0
        max_height = 0
        
        for mode in modes[:rows*cols]:  # Limit to grid capacity
            # Get first image with this mode
            image_paths = collection.get_images_by_mode(mode)
            if not image_paths:
                continue
                
            image_path = image_paths[0]
            img = Image.open(image_path)
            images.append((image_path, img, mode))
            
            max_width = max(max_width, img.width)
            max_height = max(max_height, img.height)
        
        # Padding between images
        padding = 4
        
        # Calculate grid dimensions
        grid_width = cols * max_width + (cols - 1) * padding
        grid_height = rows * max_height + (rows - 1) * padding
        
        # Create grid image
        grid_img = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # Place images in grid
        for i, (image_path, img, mode) in enumerate(images):
            if i >= rows * cols:
                break
                
            # Calculate position
            row = i // cols
            col = i % cols
            x = col * (max_width + padding)
            y = row * (max_height + padding)
            
            # Resize image to fit grid cell
            resized_img = img.resize((max_width, max_height), Image.LANCZOS)
            
            # Paste image into grid
            grid_img.paste(resized_img, (x, y))
        
        return grid_img
    
    def _generate_workflow_specific_caption(self, collection: Collection) -> str:
        """
        Generate ModeGrid-specific caption content.
        
        Args:
            collection (Collection): Collection to generate caption for
            
        Returns:
            str: ModeGrid-specific caption text
        """
        if not isinstance(collection, ModeGridCollection):
            return ""
        
        caption = "\nModeGrid Visualization Details:\n"
        
        # Add information about modes
        modes = collection.get_available_modes()
        caption += f"Showing {len(modes)} imaging modes: "
        caption += ", ".join(modes)
        caption += "\n"
        
        # Add magnification information
        caption += f"Magnification: {collection.magnification}x\n"
        
        return caption


class CompareGridController(WorkflowController):
    """Controller for CompareGrid workflow."""
    
    def get_workflow_type(self) -> str:
        return "CompareGrid"
    
    def get_collection_class(self) -> Type[Collection]:
        return CompareGridCollection
    
    def build_collections(self) -> List[Collection]:
        """
        Build collections based on CompareGrid criteria.
        
        Note: This is a placeholder implementation since CompareGrid
        requires manually selecting images from different sessions.
        
        Returns:
            List[Collection]: Empty list (collections are built manually)
        """
        # CompareGrid collections are built manually by selecting images
        # from different sample sessions, so we can't auto-generate them
        return []
    
    def validate_collection(self, collection: Collection) -> bool:
        """
        Validate a collection according to CompareGrid workflow rules.
        
        Args:
            collection (Collection): Collection to validate
            
        Returns:
            bool: True if collection is valid
        """
        if not isinstance(collection, CompareGridCollection):
            return False
        
        return collection.is_valid()
    
    def create_grid_visualization(self, collection: Collection, layout: Optional[Tuple[int, int]] = None) -> Image.Image:
        """
        Create grid visualization for a CompareGrid collection.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            
        Returns:
            Image.Image: Grid visualization image
        """
        if not isinstance(collection, CompareGridCollection):
            raise ValueError("Collection must be a CompareGridCollection")
        
        # Get sample IDs
        sample_ids = collection.get_sample_ids()
        
        # Determine grid layout
        if layout:
            rows, cols = layout
        else:
            rows, cols = self.calculate_grid_layout(len(sample_ids))
        
        # Load images and calculate max dimensions
        images = []
        max_width = 0
        max_height = 0
        
        for sample_id in sample_ids[:rows*cols]:  # Limit to grid capacity
            image_path = collection.get_image_for_sample(sample_id)
            if not image_path:
                continue
                
            img = Image.open(image_path)
            images.append((image_path, img, sample_id))
            
            max_width = max(max_width, img.width)
            max_height = max(max_height, img.height)
        
        # Additional space for sample ID text
        text_height = 30
        
        # Padding between images
        padding = 4
        
        # Calculate grid dimensions
        grid_width = cols * max_width + (cols - 1) * padding
        grid_height = rows * (max_height + text_height) + (rows - 1) * padding
        
        # Create grid image
        grid_img = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        draw = ImageDraw.Draw(grid_img)
        
        # Try to load Arial font
        try:
            # Calculate font size based on grid width
            # When image width is 6.5 inches (at 96 DPI = 624 pixels), font size should be 10pt
            target_font_size = int(10 * (max_width / 624))
            font = ImageFont.truetype("arial.ttf", target_font_size)
        except IOError:
            # Fall back to default font if Arial not available
            font = ImageFont.load_default()
        
        # Place images in grid
        for i, (image_path, img, sample_id) in enumerate(images):
            if i >= rows * cols:
                break
                
            # Calculate position
            row = i // cols
            col = i % cols
            x = col * (max_width + padding)
            y = row * (max_height + text_height + padding)
            
            # Add sample ID text
            text_y = y
            draw.text((x + 5, text_y), sample_id, fill=(0, 0, 0), font=font)
            
            # Paste image below text
            y_with_text = y + text_height
            
            # Resize image to fit grid cell
            resized_img = img.resize((max_width, max_height), Image.LANCZOS)
            
            # Paste image into grid
            grid_img.paste(resized_img, (x, y_with_text))
        
        return grid_img
    
    def _generate_workflow_specific_caption(self, collection: Collection) -> str:
        """
        Generate CompareGrid-specific caption content.
        
        Args:
            collection (Collection): Collection to generate caption for
            
        Returns:
            str: CompareGrid-specific caption text
        """
        if not isinstance(collection, CompareGridCollection):
            return ""
        
        caption = "\nCompareGrid Visualization Details:\n"
        
        # Add information about samples
        sample_ids = collection.get_sample_ids()
        caption += f"Comparing {len(sample_ids)} samples: "
        caption += ", ".join(sample_ids)
        caption += "\n"
        
        # Add mode and magnification information
        caption += f"Imaging mode: {collection.mode}\n"
        caption += f"Magnification: {collection.magnification}x\n"
        
        return caption


class MakeGridController(WorkflowController):
    """Controller for MakeGrid workflow."""
    
    def get_workflow_type(self) -> str:
        return "MakeGrid"
    
    def get_collection_class(self) -> Type[Collection]:
        return MakeGridCollection
    
    def build_collections(self) -> List[Collection]:
        """
        Build collections based on MakeGrid criteria.
        
        Note: Since MakeGrid is for manual selection, this doesn't
        automatically build collections.
        
        Returns:
            List[Collection]: Empty list (collections are built manually)
        """
        # MakeGrid collections are built manually by selecting images,
        # so we can't auto-generate them
        return []
    
    def validate_collection(self, collection: Collection) -> bool:
        """
        Validate a collection according to MakeGrid workflow rules.
        
        Args:
            collection (Collection): Collection to validate
            
        Returns:
            bool: True if collection is valid
        """
        if not isinstance(collection, MakeGridCollection):
            return False
        
        return collection.is_valid()
    
    def create_grid_visualization(self, collection: Collection, layout: Optional[Tuple[int, int]] = None) -> Image.Image:
        """
        Create grid visualization for a MakeGrid collection.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            
        Returns:
            Image.Image: Grid visualization image
        """
        if not isinstance(collection, MakeGridCollection):
            raise ValueError("Collection must be a MakeGridCollection")
        
        # Get images in specified order
        image_paths = collection.image_order
        
        # Determine grid layout
        if layout:
            rows, cols = layout
        else:
            rows, cols = self.calculate_grid_layout(len(image_paths))
        
        # Load images and calculate max dimensions
        images = []
        max_width = 0
        max_height = 0
        
        for image_path in image_paths[:rows*cols]:  # Limit to grid capacity
            img = Image.open(image_path)
            images.append((image_path, img))
            
            max_width = max(max_width, img.width)
            max_height = max(max_height, img.height)
        
        # Padding between images
        padding = 4
        
        # Calculate grid dimensions
        grid_width = cols * max_width + (cols - 1) * padding
        grid_height = rows * max_height + (rows - 1) * padding
        
        # Create grid image
        grid_img = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # Place images in grid
        for i, (image_path, img) in enumerate(images):
            if i >= rows * cols:
                break
                
            # Calculate position
            row = i // cols
            col = i % cols
            x = col * (max_width + padding)
            y = row * (max_height + padding)
            
            # Resize image to fit grid cell
            resized_img = img.resize((max_width, max_height), Image.LANCZOS)
            
            # Paste image into grid
            grid_img.paste(resized_img, (x, y))
        
        return grid_img
    
    def _generate_workflow_specific_caption(self, collection: Collection) -> str:
        """
        Generate MakeGrid-specific caption content.
        
        Args:
            collection (Collection): Collection to generate caption for
            
        Returns:
            str: MakeGrid-specific caption text
        """
        if not isinstance(collection, MakeGridCollection):
            return ""
        
        caption = "\nMakeGrid Visualization Details:\n"
        
        # Add information about number of images
        caption += f"Custom grid with {len(collection.images)} images\n"
        
        # Add basic information about first image
        if collection.images:
            first_image = collection.images[0]
            metadata = self.get_metadata(first_image)
            if metadata:
                caption += f"First image mode: {metadata.mode}\n"
                caption += f"First image magnification: {metadata.magnification}x\n"
        
        return caption


class WorkflowFactory:
    """Creates appropriate workflow controllers based on type."""
    
    @staticmethod
    def create_workflow(workflow_type: str, session: Session) -> WorkflowController:
        """
        Factory method to create workflow instances.
        
        Args:
            workflow_type (str): Type of workflow
            session (Session): Session object
            
        Returns:
            WorkflowController: Controller for the specified workflow
            
        Raises:
            ValueError: If workflow type is unknown
        """
        if workflow_type == "MagGrid":
            return MagGridController(session)
        elif workflow_type == "ModeGrid":
            return ModeGridController(session)
        elif workflow_type == "CompareGrid":
            return CompareGridController(session)
        elif workflow_type == "MakeGrid":
            return MakeGridController(session)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")


# Example usage (to be removed in final version):
if __name__ == "__main__":
    # Test workflow factory
    from models.session import Session, SessionRepository
    
    repo = SessionRepository()
    session_folder = "path/to/session/folder"
    
    if repo.session_exists(session_folder):
        session = repo.load_session(session_folder)
    else:
        session = repo.create_session(session_folder)
        session.update_field("test_user", "sample_id", "TEST-001")
        repo.save_session(session)
    
    # Create MagGrid workflow
    workflow = WorkflowFactory.create_workflow("MagGrid", session)
    
    # Load or build collections
    workflow.load_collections()
    if not workflow.collections:
        workflow.collections = workflow.build_collections()
        workflow.save_collections()
    
    # Export grid if collections exist
    if workflow.collections:
        output_path = workflow.export_grid(workflow.collections[0])
        print(f"Grid exported to: {output_path}")

        max_height = max(max_height, img.width)