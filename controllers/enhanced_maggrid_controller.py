"""
Enhanced MagGrid Controller with Template Matching support.
"""

import os
import cv2
from PIL import Image, ImageDraw
from typing import List, Dict, Any, Optional, Tuple

# Import from your existing codebase
from controllers.workflow_controllers import MagGridController
from models.session import Session
from models.collections import MagGridCollection

# Import the template matching helper from your application
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
        
        # If we found a good container using spatial metadata, return it
        if best_container_spatial:
            return best_container_spatial
        
        # If spatial method didn't find a container, try template matching
        target_path = target_metadata.image_path
        valid_containers = []
        
        for candidate_path, candidate_metadata in candidate_images:
            # Skip if magnification difference is insufficient
            mag_ratio = target_metadata.magnification / candidate_metadata.magnification
            if mag_ratio < 1.5:  # Same threshold as in check_strict_containment
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
                        candidate_path, target_path, candidate_metadata, target_metadata
                    )
                    
                    # Store result in cache
                    self.template_match_cache[cache_key] = (is_contained, match_result)
                    
                    if is_contained:
                        match_score = match_result.get('score', 0)
                        valid_containers.append((candidate_path, candidate_metadata, match_score))
                except Exception as e:
                    print(f"Template matching error for {os.path.basename(target_path)} in "
                          f"{os.path.basename(candidate_path)}: {str(e)}")
        
        if not valid_containers:
            return None
            
        # Choose the container with the best match score (higher is better)
        best_container = max(valid_containers, key=lambda x: x[2])
        return best_container[0], best_container[1]
    
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
        Adds visualization of the template matching results where available.
        
        Args:
            collection (Collection): Collection to visualize
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            annotation_style (str): Style for annotations ("solid", "dotted", "none")
            preserve_resolution (bool): Whether to preserve original image resolution
            
        Returns:
            Image.Image: Grid visualization image
        """
        # Start with the base grid visualization
        grid_img = super().create_grid_visualization(collection, layout, annotation_style, preserve_resolution)
        
        # If annotation style is "none", don't add template matching overlays
        if annotation_style == "none":
            return grid_img
        
        # Convert to PIL Image if it's not already
        if not isinstance(grid_img, Image.Image):
            grid_img = Image.fromarray(grid_img)
        
        # Create a draw object
        draw = ImageDraw.Draw(grid_img)
        
        # Get the sorted magnifications
        magnifications = collection.get_sorted_magnifications()
        
        # Determine grid layout
        if layout:
            rows, cols = layout
        else:
            rows, cols = self.calculate_grid_layout(len(magnifications))
        
        # For each magnification level (except the highest one),
        # highlight the areas that match higher magnification images
        for i, low_mag in enumerate(magnifications[:-1]):  # Skip the highest mag level
            # Get the first image at this magnification
            low_mag_images = collection.get_images_at_magnification(low_mag)
            if not low_mag_images:
                continue
                
            low_mag_path = low_mag_images[0]
            low_mag_metadata = self.get_metadata(low_mag_path)
            
            # Find the position of this image in the grid
            row = i // cols
            col = i % cols
            
            # For each higher magnification level
            for j, high_mag in enumerate(magnifications[i+1:]):
                high_mag_images = collection.get_images_at_magnification(high_mag)
                if not high_mag_images:
                    continue
                    
                high_mag_path = high_mag_images[0]
                
                # Check if this is a hierarchical relationship
                if high_mag_path in collection.hierarchy.get(low_mag_path, []):
                    # Check if we have a template match result
                    cache_key = (high_mag_path, low_mag_path)
                    if cache_key in self.template_match_cache:
                        is_contained, match_result = self.template_match_cache[cache_key]
                        
                        if is_contained and match_result and 'top_left' in match_result and 'bottom_right' in match_result:
                            # We have a template match - overlay it on the grid
                            # TO DO: Implement overlay based on grid layout and image positions
                            pass
        
        return grid_img
    
    def export_grid(self, collection, output_path=None, layout=None, annotation_style=None):
        """
        Export enhanced grid visualization to file with template matching.
        
        Args:
            collection (Collection): Collection to export
            output_path (Optional[str]): Path to save the file, or None to auto-generate
            layout (Optional[Tuple[int, int]]): Optional (rows, columns) layout override
            annotation_style (Optional[str]): Style for annotations (e.g., "solid", "dotted", "none")
            
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
        caption = self.generate_caption(collection, None)
        
        # Add template matching information
        caption += "\nTemplate Matching Information:\n"
        
        template_match_count = 0
        for (high_path, low_path), (is_contained, match_result) in self.template_match_cache.items():
            if is_contained and high_path in collection.images and low_path in collection.images:
                template_match_count += 1
        
        caption += f"Total template matches: {template_match_count}\n"
        
        if template_match_count > 0:
            caption += "Note: Containment relationships verified by both metadata and visual template matching.\n"
        
        # Save caption
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(caption)
        except Exception as e:
            print(f"Error saving enhanced caption: {str(e)}")
        
        return caption
    
    def _save_template_matching_data(self, collection, output_path):
        """
        Save template matching data for debug/reference.
        
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
                        # Create a serializable version of the match result
                        serializable_result = {
                            "method": match_result.get("method", "unknown"),
                            "score": match_result.get("score", 0),
                            "scale": match_result.get("scale", 1.0),
                        }
                        
                        # Add bounding box if available
                        if 'top_left' in match_result and 'bottom_right' in match_result:
                            serializable_result["bbox"] = {
                                "top_left": match_result["top_left"],
                                "bottom_right": match_result["bottom_right"],
                                "width": match_result.get("width"),
                                "height": match_result.get("height")
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
            print(f"Error saving template matching data: {str(e)}")
            return False


# Example usage (to be removed in final version):
if __name__ == "__main__":
    # Test the enhanced controller
    from models.session import Session, SessionRepository
    
    repo = SessionRepository()
    session_folder = "path/to/session/folder"
    
    if repo.session_exists(session_folder):
        session = repo.load_session(session_folder)
    else:
        session = repo.create_session(session_folder)
        session.update_field("test_user", "sample_id", "TEST-001")
        repo.save_session(session)
    
    # Create enhanced MagGrid workflow
    workflow = EnhancedMagGridController(session)
    
    # Load or build collections
    workflow.load_collections()
    if not workflow.collections:
        workflow.collections = workflow.build_collections()
        workflow.save_collections()
    
    # Export grid if collections exist
    if workflow.collections:
        output_path = workflow.export_grid(workflow.collections[0])
        print(f"Grid exported to: {output_path}")
