"""
Enhanced MagGrid Controller with Template Matching support.
"""

import os
import cv2
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Optional, Tuple

# Import from existing codebase
from controllers.workflow_controllers import MagGridController, WorkflowFactory
from models.session import Session
from models.collections import MagGridCollection

# Import the template matching helper
from template_matching import TemplateMatchingHelper

class EnhancedMagGridController(MagGridController):
    """
    Enhanced MagGrid workflow controller with template matching support.
    Extends the existing MagGridController to add visual template matching capabilities.
    """
    
    def __init__(self, session: Session):
        """Initialize the enhanced controller."""
        super().__init__(session)
        
        # Template matching helper
        self.template_matcher = TemplateMatchingHelper()
        
        # Cache for template matching results
        self.template_match_cache = {}  # (high_path, low_path) -> match_result
        
        # Template matching parameters
        self.match_threshold = 0.5  # Match quality threshold
    
    def get_workflow_type(self) -> str:
        """Get the workflow type string."""
        return "EnhancedMagGrid"
    
    def _find_best_container(self, target_metadata, candidate_images):
        """
        Find the best containing image for a target image using both spatial metadata
        and template matching.
        
        Args:
            target_metadata: Metadata for the target (higher magnification) image
            candidate_images: List of (path, metadata) tuples for potential container images
            
        Returns:
            Tuple of (path, metadata) for the best container, or None if none found
        """
        # First use the spatial metadata method from parent class
        best_container_spatial = super()._find_best_container(target_metadata, candidate_images)
        
        # If we found a good container using spatial metadata, also try template matching
        target_path = target_metadata.image_path
        valid_containers = []
        
        for candidate_path, candidate_metadata in candidate_images:
            # Skip if magnification difference is insufficient
            mag_ratio = target_metadata.magnification / candidate_metadata.magnification
            if mag_ratio < 1.5:
                continue
                
            # Skip if mode, voltage, or spot size don't match
            if (target_metadata.mode != candidate_metadata.mode or
                target_metadata.high_voltage_kV != candidate_metadata.high_voltage_kV or
                target_metadata.spot_size != candidate_metadata.spot_size):
                continue
            
            # Check template matching cache first
            cache_key = (target_path, candidate_path)
            if cache_key in self.template_match_cache:
                is_contained, match_result = self.template_match_cache[cache_key]
                if is_contained:
                    # Calculate a score based on match quality
                    match_score = match_result.get('score', 0)
                    valid_containers.append((candidate_path, candidate_metadata, match_score))
            else:
                # Run template matching
                try:
                    is_contained, match_result = self.template_matcher.validate_containment_with_template_matching(
                        candidate_path, target_path, candidate_metadata, target_metadata, self.match_threshold
                    )
                    
                    # Store result in cache
                    self.template_match_cache[cache_key] = (is_contained, match_result)
                    
                    if is_contained:
                        match_score = match_result.get('score', 0)
                        valid_containers.append((candidate_path, candidate_metadata, match_score))
                except Exception as e:
                    logging.error(f"Template matching error for {os.path.basename(target_path)} in "
                                f"{os.path.basename(candidate_path)}: {str(e)}")
        
        # If we found containers via template matching
        if valid_containers:
            # Choose the container with the best match score (higher is better)
            best_container = max(valid_containers, key=lambda x: x[2])
            return best_container[0], best_container[1]
        
        # If no template match found, fall back to spatial metadata result
        return best_container_spatial
    
    def build_collections(self) -> List[MagGridCollection]:
        """
        Build collections based on MagGrid criteria using enhanced containment detection.
        
        Returns:
            List[Collection]: List of generated collections
        """
        # Clear template matching cache
        self.template_match_cache = {}
        
        # Use the enhanced find_best_container method
        return super().build_collections()
    
    def _get_debug_match_image_path(self, high_path: str, low_path: str) -> Optional[str]:
        """
        Get the path to the debug match image.
        
        Args:
            high_path (str): Path to high magnification image
            low_path (str): Path to low magnification image
            
        Returns:
            Optional[str]: Path to debug match image or None if not found
        """
        debug_dir = os.path.join(os.path.dirname(low_path), "debug_matches")
        debug_filename = f"match_{os.path.basename(high_path)}_in_{os.path.basename(low_path)}.jpg"
        debug_path = os.path.join(debug_dir, debug_filename)
        
        if os.path.exists(debug_path):
            return debug_path
        return None
    
    def create_grid_visualization(self, collection, layout=None, annotation_style="solid", preserve_resolution=True):
        """
        Create grid visualization with template matching annotations.
        Only uses debug match images from disk, never falls back to originals.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            annotation_style (str): Style for annotations ("solid", "dotted", "template", "none")
            preserve_resolution (bool): Whether to preserve original image resolution
            
        Returns:
            Image.Image: Grid visualization image
        """
        # If we're not using template annotations, use parent class method
        if annotation_style != "template":
            return super().create_grid_visualization(collection, layout, annotation_style, preserve_resolution)
        
        # Get the sorted magnifications
        magnifications = collection.get_sorted_magnifications()
        
        # Determine grid layout
        if layout:
            rows, cols = layout
        else:
            rows, cols = self.calculate_grid_layout(len(magnifications))
        
        # STEP 1: Find all debug match images to use
        debug_match_images = {}
        
        # Find debug match images for each magnification level (except highest)
        for mag in magnifications:
            # Skip highest magnification (no higher-mag images will be contained in it)
            if mag == max(magnifications):
                continue
            
            # Get images at this magnification
            img_paths = collection.get_images_at_magnification(mag)
            if not img_paths:
                continue
            
            # For each image at this magnification
            for low_path in img_paths:
                # Get higher-mag images that should be contained in this one
                contained_paths = collection.hierarchy.get(low_path, [])
                if not contained_paths:
                    continue
                
                # Look for debug match images
                for high_path in contained_paths:
                    match_img_path = self._get_debug_match_image_path(high_path, low_path)
                    if match_img_path:
                        logging.info(f"Found debug match image: {match_img_path}")
                        debug_match_images[low_path] = match_img_path
                        break  # Use the first debug match image found
        
        # STEP 2: Prepare image list for grid creation
        grid_images = []
        
        # Add debug match images for all magnifications except highest
        for mag in magnifications[:rows*cols]:
            # Skip if it's the highest magnification
            if mag == max(magnifications):
                continue
                
            # Get images at this magnification
            img_paths = collection.get_images_at_magnification(mag)
            if not img_paths:
                continue
            
            img_path = img_paths[0]  # Use first image at this magnification
            
            # Only use debug match image if available
            if img_path in debug_match_images:
                try:
                    match_img = Image.open(debug_match_images[img_path])
                    grid_images.append((img_path, match_img, mag))
                    logging.info(f"Using debug match image for {os.path.basename(img_path)}")
                except Exception as e:
                    logging.error(f"Error loading debug match image {debug_match_images[img_path]}: {e}")
        
        # Add highest magnification images
        highest_mag = max(magnifications)
        highest_img_paths = collection.get_images_at_magnification(highest_mag)
        if highest_img_paths:
            try:
                highest_img = Image.open(highest_img_paths[0])
                grid_images.append((highest_img_paths[0], highest_img, highest_mag))
                logging.info(f"Using highest mag image: {os.path.basename(highest_img_paths[0])}")
            except Exception as e:
                logging.error(f"Error loading highest mag image {highest_img_paths[0]}: {e}")
        
        # If no images, return empty grid
        if not grid_images:
            logging.error("No debug match images available for grid visualization")
            return Image.new('RGB', (400, 300), (255, 255, 255))
        
        # STEP 3: Create the grid
        # Process images for grid creation
        if preserve_resolution:
            # Use original dimensions
            images_to_use = []
            for image_path, img, mag in grid_images:
                images_to_use.append((image_path, img.copy(), mag))
        else:
            # Normalize dimensions
            target_width = max(img.width for _, img, _ in grid_images)
            images_to_use = []
            for image_path, img, mag in grid_images:
                aspect_ratio = img.height / img.width
                new_height = int(target_width * aspect_ratio)
                resized_img = img.resize((target_width, new_height), Image.LANCZOS)
                images_to_use.append((image_path, resized_img, mag))
        
        # Padding between images
        padding = 4
        
        # Create grid layout
        grid_layout = []
        for r in range(rows):
            row_images = []
            for c in range(cols):
                idx = r * cols + c
                if idx < len(images_to_use):
                    row_images.append(images_to_use[idx])
            if row_images:
                grid_layout.append(row_images)
        
        # Calculate dimensions
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
                
                # Log which image is being placed
                logging.info(f"Placed image in grid: {os.path.basename(image_path)} at position ({x_pos},{y_pos})")
                
                x_offset += cell_width + padding
            
            y_offset += row_heights[r] + padding
        
        # Save a debug copy
        debug_dir = os.path.join(self.workflow_folder, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, f"grid_debug_{collection.name}.png")
        grid_img.save(debug_path)
        logging.info(f"Saved debug grid image: {debug_path}")
        
        return grid_img
    
    def export_grid(self, collection, output_path=None, layout=None, annotation_style=None):
        """
        Export enhanced grid visualization to file with template matching.
        
        Args:
            collection (Collection): Collection to export
            output_path (Optional[str]): Path to save the file, or None to auto-generate
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            annotation_style (Optional[str]): Style for annotations (e.g., "solid", "dotted", "template", "none")
            
        Returns:
            str: Path to the exported file
        """
        # Generate visualization with enhanced annotations
        grid_image = self.create_grid_visualization(collection, layout, annotation_style)
        
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
        
        # Generate enhanced caption that includes template matching info
        caption_path = output_path.replace(".png", ".txt")
        self._generate_enhanced_caption(collection, caption_path)
        
        # Also save template matching data for debugging/reference
        self._save_template_matching_data(collection, output_path.replace(".png", "_template_matches.json"))
        
        return output_path
    
    def _generate_enhanced_caption(self, collection, output_path):
        """
        Generate an enhanced caption for the grid that includes template matching info.
        
        Args:
            collection (Collection): Collection to generate caption for
            output_path (str): Path to save the caption
            
        Returns:
            str: Generated caption text
        """
        # Generate basic caption from parent method
        caption = self._generate_workflow_specific_caption(collection)
        
        # Add template matching information
        caption += "\nTemplate Matching Information:\n"
        
        template_match_count = 0
        match_scores = []
        
        for (high_path, low_path), (is_contained, match_result) in self.template_match_cache.items():
            if is_contained and high_path in collection.images and low_path in collection.images:
                template_match_count += 1
                if 'score' in match_result:
                    match_scores.append(match_result['score'])
        
        caption += f"Total template matches: {template_match_count}\n"
        
        if template_match_count > 0:
            caption += f"Average match score: {sum(match_scores)/len(match_scores):.3f}\n" if match_scores else ""
            caption += "Note: Containment relationships verified by visual template matching.\n"
        
        # Save caption
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(caption)
        except Exception as e:
            logging.error(f"Error saving enhanced caption: {str(e)}")
        
        return caption
    
    def _save_template_matching_data(self, collection, output_path):
        """
        Save template matching data for debug/reference.
        Includes detailed coordinate information for troubleshooting.
        
        Args:
            collection (Collection): Collection to save data for
            output_path (str): Path to save the data
            
        Returns:
            bool: True if successful
        """
        try:
            # Extract relevant template match data for this collection
            matches_data = {}
            for (high_path, low_path), (is_contained, match_result) in self.template_match_cache.items():
                if high_path in collection.images and low_path in collection.images:
                    high_name = os.path.basename(high_path)
                    low_name = os.path.basename(low_path)
                    
                    if is_contained and match_result:
                        # Create detailed match result for debugging
                        serializable_result = {
                            "score": match_result.get("score", 0),
                            "scale": match_result.get("scale", 1.0),
                        }
                        
                        # Original template matching results
                        if 'top_left' in match_result and 'bottom_right' in match_result:
                            serializable_result["original_bbox"] = {
                                "top_left": list(match_result["top_left"]),  # Convert tuples to lists for JSON
                                "bottom_right": list(match_result["bottom_right"]),
                                "width": match_result.get("width"),
                                "height": match_result.get("height")
                            }
                        
                        # Add image dimensions if available
                        if 'low_img_shape' in match_result:
                            serializable_result["low_img_shape"] = list(match_result["low_img_shape"])
                        if 'high_img_shape' in match_result:
                            serializable_result["high_img_shape"] = list(match_result["high_img_shape"])
                        
                        # Add debug match image path
                        debug_match_path = self._get_debug_match_image_path(high_path, low_path)
                        if debug_match_path:
                            serializable_result["debug_match_path"] = debug_match_path
                            
                        matches_data[f"{high_name} in {low_name}"] = serializable_result
            
            # Save to file
            if matches_data:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    import json
                    json.dump(matches_data, f, indent=4)
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error saving template matching data: {str(e)}")
            return False