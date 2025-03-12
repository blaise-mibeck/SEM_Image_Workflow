"""
Template matching module for SEM images.
Provides functionality to locate high magnification images within low magnification images.
"""

import cv2
import numpy as np
import os
import logging
from typing import Dict, Tuple, Any, Optional


class TemplateMatchingHelper:
    """Helper class for template matching between SEM images."""
    
    def __init__(self):
        """Initialize the template matching helper."""
        self.default_threshold = 0.5
        logging.info("TemplateMatchingHelper initialized with default threshold: %f", self.default_threshold)
    
    def crop_and_resize_template(self, high_img, high_meta, low_meta):
        """
        Crop the high magnification image and resize it to match the scale in the low magnification image.
        
        Args:
            high_img: High magnification image array
            high_meta: Metadata for high magnification image
            low_meta: Metadata for low magnification image
            
        Returns:
            tuple: (resized_template, scale) - Resized template image and scale factor used
        """
        # Define the cropping coordinates (full image for now)
        startX = 0
        startY = 0
        endX = high_meta.pixels_width
        endY = high_meta.pixels_height
        
        # Calculate scale based on field of view ratio
        scale = high_meta.field_of_view_width / low_meta.field_of_view_width
        
        # Calculate new dimensions
        new_width = int(endX * scale)
        new_height = int(endY * scale)
        
        # Log dimensions for debugging
        logging.debug("Template resize: original %dx%d → scaled %dx%d (scale: %f)", 
                     endX, endY, new_width, new_height, scale)
        
        # Crop the image
        cropped_image = high_img[startY:endY, startX:endX]
        
        # Resize to match scale in low magnification image
        resized_template = cv2.resize(cropped_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        return resized_template, scale
    
    def validate_containment_with_template_matching(
            self, 
            low_img_path: str, 
            high_img_path: str, 
            low_meta: Any, 
            high_meta: Any, 
            threshold: Optional[float] = None
        ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate that a high magnification image is contained within a low magnification image
        using template matching with cv2.TM_CCOEFF_NORMED.
        
        Args:
            low_img_path: Path to low magnification image
            high_img_path: Path to high magnification image
            low_meta: Metadata for low magnification image
            high_meta: Metadata for high magnification image
            threshold: Match threshold (default uses self.default_threshold)
            
        Returns:
            Tuple[bool, Dict[str, Any]]: Boolean indicating containment and match details
        """
        # Set default threshold if not provided
        if threshold is None:
            threshold = self.default_threshold
            
        # Start logging the matching process
        logging.info("Template matching: %s in %s", 
                     os.path.basename(high_img_path), 
                     os.path.basename(low_img_path))
            
        try:
            # First check metadata to ensure basic requirements are met
            if (high_meta.mode != low_meta.mode or
                high_meta.high_voltage_kV != low_meta.high_voltage_kV or
                high_meta.spot_size != low_meta.spot_size):
                logging.info("Metadata mismatch: mode, voltage, or spot size doesn't match")
                return False, {"error": "Metadata mismatch"}
                
            # Check magnification ratio
            mag_ratio = high_meta.magnification / low_meta.magnification
            if mag_ratio < 1.5:
                logging.info("Insufficient magnification difference: %.2f (need ≥ 1.5)", mag_ratio)
                return False, {"error": f"Insufficient magnification difference: {mag_ratio:.2f}"}
            
            logging.debug("Magnification ratio: %.2f", mag_ratio)
            
            # Load images and convert to grayscale
            low_img = cv2.imread(low_img_path, cv2.IMREAD_GRAYSCALE)
            high_img = cv2.imread(high_img_path, cv2.IMREAD_GRAYSCALE)
            
            if low_img is None or high_img is None:
                logging.error("Failed to load images")
                return False, {"error": "Failed to load images"}
                
            logging.debug("Low image shape: %s, High image shape: %s", 
                         str(low_img.shape), str(high_img.shape))
            
            # Crop and resize template
            template, scale = self.crop_and_resize_template(high_img, high_meta, low_meta)
            
            # Get template dimensions
            h, w = template.shape
            
            if h > low_img.shape[0] or w > low_img.shape[1]:
                logging.error("Template larger than source image")
                return False, {"error": "Template larger than source image"}
                
            # Apply template matching with TM_CCOEFF_NORMED
            result = cv2.matchTemplate(low_img, template, cv2.TM_CCOEFF_NORMED)
            
            # Find best match location
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            score = max_val
            top_left = max_loc
                
            # Calculate bottom right point
            bottom_right = (top_left[0] + w, top_left[1] + h)
            
            logging.info("Match score: %.4f (threshold: %.4f)", score, threshold)
            logging.debug("Match location: Top-left: %s, Bottom-right: %s", 
                         str(top_left), str(bottom_right))
            
            # Check if score meets threshold
            if score > threshold:
                # Create match result with comprehensive debug info
                match_result = {
                    "score": score,
                    "scale": scale,
                    "top_left": top_left,
                    "bottom_right": bottom_right,
                    "width": w,
                    "height": h,
                    "low_img_shape": low_img.shape,
                    "high_img_shape": high_img.shape,
                    "low_img_meta": {
                        "path": low_img_path,
                        "magnification": low_meta.magnification,
                        "field_of_view": (low_meta.field_of_view_width, low_meta.field_of_view_height),
                        "position": (low_meta.sample_position_x, low_meta.sample_position_y)
                    },
                    "high_img_meta": {
                        "path": high_img_path,
                        "magnification": high_meta.magnification,
                        "field_of_view": (high_meta.field_of_view_width, high_meta.field_of_view_height),
                        "position": (high_meta.sample_position_x, high_meta.sample_position_y)
                    }
                }
                
                # Save a visualization of the match for debugging if needed
                try:
                    debug_dir = os.path.join(os.path.dirname(low_img_path), "debug_matches")
                    os.makedirs(debug_dir, exist_ok=True)
                    
                    # Create a visualization showing the match
                    low_img_color = cv2.imread(low_img_path)
                    if low_img_color is not None:
                        # Draw rectangle marking match position
                        cv2.rectangle(low_img_color, top_left, bottom_right, (0, 0, 255), 2)
                        
                        # Add text with score
                        text_pos = (top_left[0], top_left[1] - 10)
                        cv2.putText(low_img_color, f"Score: {score:.2f}", text_pos, 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
                        # Save debug image
                        debug_filename = f"match_{os.path.basename(high_img_path)}_in_{os.path.basename(low_img_path)}.jpg"
                        debug_path = os.path.join(debug_dir, debug_filename)
                        cv2.imwrite(debug_path, low_img_color)
                        
                        logging.debug("Saved debug match visualization: %s", debug_path)
                except Exception as e:
                    logging.debug("Failed to save debug visualization: %s", str(e))
                
                return True, match_result
            else:
                return False, {"error": f"Match score {score:.4f} below threshold", "score": score}
                
        except Exception as e:
            logging.error("Error in template matching: %s", str(e))
            return False, {"error": str(e)}