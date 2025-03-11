import os
import numpy as np
import cv2
from PIL import Image, ImageDraw
from typing import Tuple, Optional, Dict, List, Any

class TemplateMatchingHelper:
    """
    Helper class for template matching between SEM images.
    
    This class provides functionality to identify high magnification images
    within low magnification images using OpenCV template matching.
    """
    
    def __init__(self):
        """Initialize the template matching helper."""
        self.methods = {
            'cv2.TM_CCOEFF': cv2.TM_CCOEFF,
            'cv2.TM_CCOEFF_NORMED': cv2.TM_CCOEFF_NORMED,
            'cv2.TM_CCORR': cv2.TM_CCORR,
            'cv2.TM_CCORR_NORMED': cv2.TM_CCORR_NORMED,
            'cv2.TM_SQDIFF': cv2.TM_SQDIFF,
            'cv2.TM_SQDIFF_NORMED': cv2.TM_SQDIFF_NORMED
        }
        
    def preprocess_images(self, img_low_mag: np.ndarray, img_high_mag: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess images for template matching.
        Crops data bar from high mag image and enhances both images.
        
        Args:
            img_low_mag (np.ndarray): Low magnification image
            img_high_mag (np.ndarray): High magnification image
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Preprocessed low and high magnification images
        """
        # Crop the data bar from high mag image
        # The data bar is at the bottom, so we keep only the top part (usually 1080px height)
        if img_high_mag is not None and len(img_high_mag.shape) >= 2:
            # Standard SEM image height is 1080px, data bar makes it around 1147px
            std_height = 1080
            actual_height = img_high_mag.shape[0]
            
            # If image is taller than standard height, crop it
            if actual_height > std_height:
                img_high_mag = img_high_mag[:std_height, :]
        
        # Convert to grayscale if they are color images
        if len(img_low_mag.shape) > 2 and img_low_mag.shape[2] > 1:
            img_low_mag_gray = cv2.cvtColor(img_low_mag, cv2.COLOR_BGR2GRAY)
        else:
            img_low_mag_gray = img_low_mag.copy()
            
        if len(img_high_mag.shape) > 2 and img_high_mag.shape[2] > 1:
            img_high_mag_gray = cv2.cvtColor(img_high_mag, cv2.COLOR_BGR2GRAY)
        else:
            img_high_mag_gray = img_high_mag.copy()
        
        # Apply histogram equalization to improve contrast
        img_low_mag_eq = cv2.equalizeHist(img_low_mag_gray)
        img_high_mag_eq = cv2.equalizeHist(img_high_mag_gray)
        
        # Optional: Apply additional preprocessing like denoising or edge enhancement
        # img_low_mag_eq = cv2.GaussianBlur(img_low_mag_eq, (5, 5), 0)
        # img_high_mag_eq = cv2.GaussianBlur(img_high_mag_eq, (5, 5), 0)
        
        return img_low_mag_eq, img_high_mag_eq
    
    def resize_template(self, img_high_mag: np.ndarray, low_mag: float, high_mag: float) -> np.ndarray:
        """
        Resize high magnification image based on the magnification ratio.
        
        Args:
            img_high_mag (np.ndarray): High magnification image
            low_mag (float): Low magnification value
            high_mag (float): High magnification value
            
        Returns:
            np.ndarray: Resized high magnification image
        """
        if low_mag <= 0 or high_mag <= 0:
            return img_high_mag  # Return original if invalid magnification
            
        # Calculate the scale factor based on magnification ratio
        scale_factor = low_mag / high_mag
        
        # Resize the high mag image to match its expected size in the low mag image
        if scale_factor < 1.0:
            # Only resize if high mag is actually higher than low mag
            height, width = img_high_mag.shape[:2]
            new_height, new_width = int(height * scale_factor), int(width * scale_factor)
            
            # Ensure dimensions are at least 1 pixel
            new_height = max(1, new_height)
            new_width = max(1, new_width)
            
            resized_img = cv2.resize(img_high_mag, (new_width, new_height), interpolation=cv2.INTER_AREA)
            return resized_img
        
        return img_high_mag
    
    def estimate_scale_from_metadata(self, high_metadata: Any, low_metadata: Any) -> float:
        """
        Estimate the scale factor between high and low magnification images from metadata.
        
        Args:
            high_metadata (Any): Metadata for higher magnification image
            low_metadata (Any): Metadata for lower magnification image
            
        Returns:
            float: Estimated scale factor
        """
        # If magnification data is available, use that
        if hasattr(high_metadata, 'magnification') and hasattr(low_metadata, 'magnification'):
            if high_metadata.magnification and low_metadata.magnification:
                return low_metadata.magnification / high_metadata.magnification
        
        # If field of view data is available, use that
        if (hasattr(high_metadata, 'field_of_view_width') and hasattr(low_metadata, 'field_of_view_width') and
            high_metadata.field_of_view_width and low_metadata.field_of_view_width):
            return high_metadata.field_of_view_width / low_metadata.field_of_view_width
            
        # Default scale factor if metadata is not available
        return 0.3  # Assumption: high mag image is roughly 30% of low mag image
    
    def match_template(self, img_low_mag: np.ndarray, img_high_mag: np.ndarray, 
                      method: str = 'cv2.TM_CCOEFF_NORMED', threshold: float = 0.5) -> Optional[Dict]:
        """
        Perform template matching to find high mag image in low mag image.
        
        Args:
            img_low_mag (np.ndarray): Low magnification image
            img_high_mag (np.ndarray): High magnification image
            method (str): OpenCV template matching method
            threshold (float): Matching threshold
            
        Returns:
            Optional[Dict]: Matching result or None if no good match found
        """
        # Check if images are valid
        if img_low_mag is None or img_high_mag is None:
            return None
            
        # Check if template (high mag) is larger than source (low mag)
        if (img_high_mag.shape[0] > img_low_mag.shape[0] or
            img_high_mag.shape[1] > img_low_mag.shape[1]):
            return None
        
        # Get the method
        tm_method = self.methods.get(method, cv2.TM_CCOEFF_NORMED)
        
        # Perform template matching
        result = cv2.matchTemplate(img_low_mag, img_high_mag, tm_method)
        
        # Different handling based on method
        if tm_method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            # For these methods, smaller values indicate better matches
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            match_val = min_val
            match_loc = min_loc
            # Convert to a normalized score (0 is worst, 1 is best)
            match_score = 1.0 - min_val if tm_method == cv2.TM_SQDIFF_NORMED else 1.0 / (1.0 + min_val)
        else:
            # For these methods, larger values indicate better matches
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            match_val = max_val
            match_loc = max_loc
            match_score = max_val if tm_method in [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED] else max_val / (np.max(img_low_mag) * np.sum(img_high_mag))
        
        # Check if match is good enough
        if (tm_method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] and match_score < threshold) or \
           (tm_method not in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED] and match_score < threshold):
            return None
        
        # Calculate bounding box
        h, w = img_high_mag.shape[:2]
        x, y = match_loc
        bbox = {
            'top_left': (x, y),
            'bottom_right': (x + w, y + h),
            'width': w,
            'height': h,
            'center': (x + w // 2, y + h // 2),
            'score': match_score,
            'method': method
        }
        
        return bbox
    
    def find_high_mag_in_low_mag(self, low_mag_path: str, high_mag_path: str, 
                                low_metadata: Optional[Any] = None, high_metadata: Optional[Any] = None,
                                multi_scale: bool = True, scale_range: Tuple[float, float, float] = (0.1, 1.0, 0.1),
                                method: str = 'cv2.TM_CCOEFF_NORMED', threshold: float = 0.5) -> Optional[Dict]:
        """
        Find a high magnification image within a low magnification image.
        
        Args:
            low_mag_path (str): Path to low magnification image
            high_mag_path (str): Path to high magnification image
            low_metadata (Optional[Any]): Metadata for low magnification image
            high_metadata (Optional[Any]): Metadata for high magnification image
            multi_scale (bool): Whether to try multiple scales
            scale_range (Tuple[float, float, float]): Range of scales to try (min, max, step)
            method (str): OpenCV template matching method
            threshold (float): Matching threshold
            
        Returns:
            Optional[Dict]: Matching result or None if no good match found
        """
        # Read images
        img_low_mag = cv2.imread(low_mag_path)
        img_high_mag = cv2.imread(high_mag_path)
        
        if img_low_mag is None or img_high_mag is None:
            return None
        
        # Check if we should crop the high mag image based on metadata
        if high_metadata and hasattr(high_metadata, 'pixels_height'):
            # If metadata specifies the correct image height (without data bar)
            std_height = high_metadata.pixels_height
            actual_height = img_high_mag.shape[0]
            
            # If image is taller than metadata height, crop it
            if actual_height > std_height and std_height > 0:
                img_high_mag = img_high_mag[:std_height, :]
        else:
            # Fallback to standard height of 1080 if no metadata
            std_height = 1080
            actual_height = img_high_mag.shape[0]
            
            # If image is significantly taller than standard height, crop it
            if actual_height > std_height + 30:  # Add buffer to avoid cropping images that don't have data bar
                img_high_mag = img_high_mag[:std_height, :]
        
        # Preprocess images
        img_low_mag_proc, img_high_mag_proc = self.preprocess_images(img_low_mag, img_high_mag)
        
        best_match = None
        best_score = -float('inf') if method not in ['cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED'] else float('inf')
        
        # If metadata is available, try to estimate the scale
        if multi_scale and low_metadata and high_metadata:
            estimated_scale = self.estimate_scale_from_metadata(high_metadata, low_metadata)
            
            # Use a range around the estimated scale
            min_scale = max(0.1, estimated_scale * 0.7)
            max_scale = min(1.0, estimated_scale * 1.3)
            scale_range = (min_scale, max_scale, 0.05)
        
        if multi_scale:
            # Try different scales
            min_scale, max_scale, scale_step = scale_range
            for scale in np.arange(min_scale, max_scale, scale_step):
                # Resize the high mag image
                h, w = img_high_mag_proc.shape[:2]
                new_h, new_w = int(h * scale), int(w * scale)
                
                # Ensure dimensions are at least 1 pixel
                if new_h < 1 or new_w < 1:
                    continue
                    
                resized_high_mag = cv2.resize(img_high_mag_proc, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                # Skip if resized image is larger than low mag image
                if resized_high_mag.shape[0] > img_low_mag_proc.shape[0] or resized_high_mag.shape[1] > img_low_mag_proc.shape[1]:
                    continue
                
                # Perform template matching
                match = self.match_template(img_low_mag_proc, resized_high_mag, method, threshold)
                
                if match:
                    match['scale'] = scale
                    
                    # Update best match based on method
                    if method in ['cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']:
                        if match['score'] < best_score:
                            best_score = match['score']
                            best_match = match
                    else:
                        if match['score'] > best_score:
                            best_score = match['score']
                            best_match = match
        else:
            # Try a single scale (either using metadata or default)
            if low_metadata and high_metadata and hasattr(low_metadata, 'magnification') and hasattr(high_metadata, 'magnification'):
                if low_metadata.magnification and high_metadata.magnification:
                    resized_high_mag = self.resize_template(img_high_mag_proc, low_metadata.magnification, high_metadata.magnification)
                    match = self.match_template(img_low_mag_proc, resized_high_mag, method, threshold)
                    if match:
                        match['scale'] = low_metadata.magnification / high_metadata.magnification
                        best_match = match
            else:
                # Try with original size
                match = self.match_template(img_low_mag_proc, img_high_mag_proc, method, threshold)
                if match:
                    match['scale'] = 1.0
                    best_match = match
        
        return best_match
    
    def visualize_match(self, low_mag_path: str, high_mag_path: str, match_result: Dict) -> Image.Image:
        """
        Create a visualization of the template match.
        
        Args:
            low_mag_path (str): Path to low magnification image
            high_mag_path (str): Path to high magnification image
            match_result (Dict): Matching result from find_high_mag_in_low_mag
            
        Returns:
            Image.Image: Visualization image
        """
        # Read images using PIL
        low_mag_img = Image.open(low_mag_path)
        high_mag_img = Image.open(high_mag_path)
        
        # Crop data bar from high mag image if needed
        high_mag_np = np.array(high_mag_img)
        if high_mag_np.shape[0] > 1080:
            high_mag_img = Image.fromarray(high_mag_np[:1080, :])
        
        # Create a copy for drawing
        img_result = low_mag_img.copy()
        draw = ImageDraw.Draw(img_result)
        
        # Draw bounding box
        x1, y1 = match_result['top_left']
        x2, y2 = match_result['bottom_right']
        
        # Use a bright color for visibility
        box_color = (255, 0, 0)  # Red
        
        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline=box_color, width=2)
        
        # Add match information
        text_pos = (x1, y1 - 20) if y1 > 20 else (x1, y2 + 5)
        scale = match_result.get('scale', 1.0)
        score = match_result.get('score', 0.0)
        
        draw.text(text_pos, f"Scale: {scale:.2f}, Score: {score:.2f}", fill=box_color)
        
        return img_result
    
    def validate_containment_with_template_matching(self, low_mag_path: str, high_mag_path: str, 
                                                 low_metadata: Any, high_metadata: Any,
                                                 method: str = 'cv2.TM_CCOEFF_NORMED', 
                                                 threshold: float = 0.5) -> Tuple[bool, Optional[Dict]]:
        """
        Validate that a high magnification image is contained within a low magnification image
        using both metadata and template matching.
        
        Args:
            low_mag_path (str): Path to low magnification image
            high_mag_path (str): Path to high magnification image
            low_metadata (Any): Metadata for low magnification image
            high_metadata (Any): Metadata for high magnification image
            method (str): OpenCV template matching method
            threshold (float): Matching threshold
            
        Returns:
            Tuple[bool, Optional[Dict]]: (is_contained, match_result)
        """
        # First check containment using metadata (if possible)
        metadata_containment = False
        
        if hasattr(low_metadata, 'check_containment'):
            metadata_containment, _ = low_metadata.check_containment(high_metadata)
        
        # Then check using template matching
        match_result = self.find_high_mag_in_low_mag(
            low_mag_path, high_mag_path, 
            low_metadata, high_metadata,
            multi_scale=True, 
            method=method, 
            threshold=threshold
        )
        
        # Determine final result
        if match_result:
            # If metadata check fails but template matching succeeds with high score
            if not metadata_containment and match_result['score'] > threshold * 1.5:
                return True, match_result
            # If metadata check passes and template matching succeeds
            elif metadata_containment:
                return True, match_result
            # If just template matching succeeds with a good score
            elif match_result['score'] > threshold:
                return True, match_result
        
        # If template matching fails but metadata check passes with high confidence
        if metadata_containment and not match_result:
            # Create a dummy match result based on metadata
            if (hasattr(high_metadata, 'sample_position_x') and hasattr(high_metadata, 'sample_position_y') and
                hasattr(low_metadata, 'sample_position_x') and hasattr(low_metadata, 'sample_position_y') and
                hasattr(high_metadata, 'field_of_view_width') and hasattr(high_metadata, 'field_of_view_height')):
                
                # Get image dimensions
                img_low_mag = cv2.imread(low_mag_path, cv2.IMREAD_GRAYSCALE)
                if img_low_mag is not None:
                    low_h, low_w = img_low_mag.shape[:2]
                    
                    # Calculate relative position in the low mag image
                    low_fov_width = low_metadata.field_of_view_width
                    low_fov_height = low_metadata.field_of_view_height
                    low_pos_x = low_metadata.sample_position_x
                    low_pos_y = low_metadata.sample_position_y
                    
                    high_fov_width = high_metadata.field_of_view_width
                    high_fov_height = high_metadata.field_of_view_height
                    high_pos_x = high_metadata.sample_position_x
                    high_pos_y = high_metadata.sample_position_y
                    
                    # Calculate position in pixels
                    # First find the bounds of the low mag image in sample coordinates
                    low_left = low_pos_x - (low_fov_width / 2)
                    low_top = low_pos_y - (low_fov_height / 2)
                    
                    # Then find the relative position of the high mag image
                    high_left = high_pos_x - (high_fov_width / 2)
                    high_top = high_pos_y - (high_fov_height / 2)
                    
                    # Convert to pixel coordinates
                    x1 = int((high_left - low_left) / low_fov_width * low_w)
                    y1 = int((high_top - low_top) / low_fov_height * low_h)
                    
                    # Calculate width and height in pixels
                    w = int(high_fov_width / low_fov_width * low_w)
                    h = int(high_fov_height / low_fov_height * low_h)
                    
                    x2 = x1 + w
                    y2 = y1 + h
                    
                    # Create a match result
                    metadata_match = {
                        'top_left': (x1, y1),
                        'bottom_right': (x2, y2),
                        'width': w,
                        'height': h,
                        'center': (x1 + w // 2, y1 + h // 2),
                        'score': 0.8,  # Arbitrary score for metadata-based match
                        'method': 'metadata',
                        'scale': high_metadata.magnification / low_metadata.magnification if hasattr(high_metadata, 'magnification') and hasattr(low_metadata, 'magnification') else None
                    }
                    
                    return True, metadata_match
        
        return False, match_result

# Example integration with the SEM Image Workflow Manager
def integrate_template_matching(workflow_controller, high_mag_path, low_mag_path, high_metadata, low_metadata):
    """
    Integrate template matching into a workflow controller.
    
    Args:
        workflow_controller: The workflow controller instance
        high_mag_path (str): Path to high magnification image
        low_mag_path (str): Path to low magnification image
        high_metadata: Metadata for high magnification image
        low_metadata: Metadata for low magnification image
        
    Returns:
        Tuple[bool, Dict]: (is_contained, result_dict)
    """
    template_matcher = TemplateMatchingHelper()
    
    # Check containment using template matching
    is_contained, match_result = template_matcher.validate_containment_with_template_matching(
        low_mag_path, high_mag_path, low_metadata, high_metadata
    )
    
    result = {
        'is_contained': is_contained,
        'match_details': match_result
    }
    
    # If match found, create a visualization
    if is_contained and match_result:
        visualization = template_matcher.visualize_match(low_mag_path, high_mag_path, match_result)
        
        # Save visualization if needed
        # visualization_path = os.path.join(os.path.dirname(low_mag_path), 'match_visualizations')
        # os.makedirs(visualization_path, exist_ok=True)
        # viz_filename = f"match_{os.path.basename(low_mag_path)}_{os.path.basename(high_mag_path)}.png"
        # visualization.save(os.path.join(visualization_path, viz_filename))
        
        result['visualization'] = visualization
    
    return is_contained, result