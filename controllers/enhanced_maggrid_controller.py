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
    
    def create_grid_visualization(self, collection, layout=None, annotation_style="solid", preserve_resolution=True):
        """
        Create enhanced grid visualization for a MagGrid collection.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            annotation_style (str): Style for annotations ("solid", "dotted", "template", "none")
            preserve_resolution (bool): Whether to preserve original image resolution
            
        Returns:
            Image.Image: Grid visualization image
        """
        # Start with the base grid visualization (without annotations if we're using template)
        if annotation_style == "template":
            base_annotation_style = "none"  # No standard annotations if using template
        else:
            base_annotation_style = annotation_style
            
        grid_img = super().create_grid_visualization(collection, layout, base_annotation_style, preserve_resolution)
        
        # If annotation style is "none" or not "template", just return the base grid
        if annotation_style == "none" or annotation_style != "template":
            return grid_img
            
        # Convert to PIL Image if it's not already
        if not isinstance(grid_img, Image.Image):
            grid_img = Image.fromarray(np.array(grid_img))
        
        # Create a draw object
        draw = ImageDraw.Draw(grid_img)
        
        # Get the sorted magnifications
        magnifications = collection.get_sorted_magnifications()
        
        # Determine grid layout
        if layout:
            rows, cols = layout
        else:
            rows, cols = self.calculate_grid_layout(len(magnifications))
            
        # Load images and get their positions in the grid
        images_info = []
        
        # Dictionary to store exact image positions in the grid
        grid_positions = {}
        
        # First, populate image positions in the grid
        for i, mag in enumerate(magnifications[:rows*cols]):
            # Calculate grid position
            row = i // cols
            col = i % cols
            
            # Get first image at this magnification
            img_paths = collection.get_images_at_magnification(mag)
            if not img_paths:
                continue
                
            img_path = img_paths[0]
            
            # Calculate cell position
            cell_width = grid_img.width // cols
            cell_height = grid_img.height // rows
            cell_x = col * cell_width
            cell_y = row * cell_height
            
            # Open the image to get dimensions
            with Image.open(img_path) as img:
                img_width, img_height = img.size
            
            # Calculate the exact position where the image is placed in the grid
            # This is based on the exact centering logic in the parent class
            x_pos = cell_x + (cell_width - img_width) // 2
            y_pos = cell_y + (cell_height - img_height) // 2
            
            # Store the position info
            grid_positions[img_path] = {
                'x': x_pos,
                'y': y_pos,
                'width': img_width,
                'height': img_height
            }
            
            images_info.append({
                'mag': mag,
                'path': img_path,
                'row': row,
                'col': col,
                'cell_x': cell_x,
                'cell_y': cell_y,
                'cell_width': cell_width,
                'cell_height': cell_height,
                'x_pos': x_pos,
                'y_pos': y_pos,
                'width': img_width,
                'height': img_height
            })
        
        # Now draw template match boxes using the cached match results
        for low_idx, low_info in enumerate(images_info[:-1]):  # Skip highest mag
            low_mag_path = low_info['path']
            
            # Check for matches with higher magnification images
            for high_info in images_info[low_idx+1:]:
                high_mag_path = high_info['path']
                
                # Skip if not in hierarchy
                if high_mag_path not in collection.hierarchy.get(low_mag_path, []):
                    continue
                
                # Check template match cache
                cache_key = (high_mag_path, low_mag_path)
                if cache_key not in self.template_match_cache:
                    continue
                    
                is_contained, match_result = self.template_match_cache[cache_key]
                
                if not is_contained or 'top_left' not in match_result or 'bottom_right' not in match_result:
                    continue
                
                # Get the original match coordinates
                top_left = match_result['top_left']
                bottom_right = match_result['bottom_right']
                
                # Get the position of the low mag image in the grid
                low_img_pos = grid_positions.get(low_mag_path)
                if not low_img_pos:
                    continue
                
                # Calculate the box position in the grid
                grid_x1 = low_img_pos['x'] + top_left[0]
                grid_y1 = low_img_pos['y'] + top_left[1]
                grid_x2 = low_img_pos['x'] + bottom_right[0]
                grid_y2 = low_img_pos['y'] + bottom_right[1]
                
                # Draw rectangle
                draw.rectangle([grid_x1, grid_y1, grid_x2, grid_y2], outline=(255, 0, 0), width=3)
                
                # Draw a second rectangle slightly inside for better visibility
                inner_margin = 2
                if grid_x2 - grid_x1 > 10 and grid_y2 - grid_y1 > 10:  # Only if big enough
                    draw.rectangle([
                        grid_x1 + inner_margin, 
                        grid_y1 + inner_margin, 
                        grid_x2 - inner_margin, 
                        grid_y2 - inner_margin
                    ], outline=(255, 255, 0), width=1)
                
                # Add match score if available
                if 'score' in match_result:
                    score = match_result['score']
                    try:
                        font = ImageFont.truetype("arial.ttf", 10)
                    except:
                        font = ImageFont.load_default()
                        
                    score_text = f"{score:.2f}"
                    draw.text((grid_x1 + 5, grid_y1 + 5), score_text, fill=(255, 0, 0), font=font)
                
                # Store the grid coordinates in the match result for later reference
                match_result['grid_box'] = {
                    'top_left': (grid_x1, grid_y1),
                    'bottom_right': (grid_x2, grid_y2)
                }
            
        # Create a debug grid with helper visualization
        debug_img = grid_img.copy()
        debug_draw = ImageDraw.Draw(debug_img)
        
        # Draw grid cell borders for debugging
        for info in images_info:
            # Draw cell border (green)
            debug_draw.rectangle([
                info['cell_x'], info['cell_y'], 
                info['cell_x'] + info['cell_width'] - 1, 
                info['cell_y'] + info['cell_height'] - 1
            ], outline=(0, 255, 0), width=1)
            
            # Draw image border (blue)
            debug_draw.rectangle([
                info['x_pos'], info['y_pos'],
                info['x_pos'] + info['width'] - 1,
                info['y_pos'] + info['height'] - 1
            ], outline=(0, 0, 255), width=1)
        
        # Save debug grid image
        debug_dir = os.path.join(self.workflow_folder, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        debug_img.save(os.path.join(debug_dir, f"grid_debug_{collection.name}.png"))
        
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
                            
                        # Grid box coordinates if available
                        if 'grid_box' in match_result:
                            serializable_result["grid_box"] = {
                                "top_left": list(match_result["grid_box"]["top_left"]),
                                "bottom_right": list(match_result["grid_box"]["bottom_right"])
                            }
                        
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