# SEM Template Matching for Image Workflow Manager

This module adds template matching capabilities to the SEM Image Workflow Manager, allowing you to identify and verify containment relationships between images at different magnifications based on visual features rather than just metadata coordinates.

## Overview

The template matching functionality enhances the MagGrid workflow by:

1. Visually identifying high magnification images within low magnification images
2. Finding containment relationships that might be missed using only metadata
3. Providing accurate bounding box visualizations of the contained areas
4. Improving the quality of grid visualizations by showing precise regions

## Installation

1. Copy the following files to your SEM Image Workflow Manager project directory:
   - `template_matching.py` - Core template matching implementation
   - `enhanced_maggrid_controller.py` - Enhanced MagGrid controller with template matching
   - `template_matching_plugin.py` - Plugin for the GUI application
   - `template_matching_test.py` - Standalone test script

2. Install required dependencies:
   ```bash
   pip install opencv-python numpy pillow
   ```

3. Initialize the plugin in your application. Add the following to your `main.py` file:
   ```python
   # After initializing the main application
   from template_matching_plugin import initialize_plugin
   plugin = initialize_plugin(app)
   ```

## Usage

### Using the GUI Plugin

1. Open the SEM Image Workflow Manager
2. Load a session containing SEM images with metadata
3. From the Tools menu, select "Template Matching..."
4. Configure the template matching options:
   - **Matching Method**: Algorithm to use for matching (TM_CCOEFF_NORMED recommended)
   - **Threshold**: Minimum matching score (0.5 is a good starting point)
   - **Multi-Scale**: Enable to find matches at different scales
   - **Use with MagGrid**: Apply results to enhance MagGrid workflow
5. Click "Run Template Matching" to process images
6. Review the results and visualizations saved to the session folder

### Enhancing MagGrid Workflow

To use the enhanced MagGrid controller with template matching:

1. From the Tools menu, select "Use Enhanced MagGrid"
2. This replaces the standard MagGrid controller with the enhanced version
3. Now when you build collections, the system will use both metadata and template matching
4. Export your grids to see improved visualizations with accurate containment areas

### Using the Test Script

For standalone template matching without the full application:

```bash
python template_matching_test.py --session /path/to/session_folder --method cv2.TM_CCOEFF_NORMED --threshold 0.5 --multi-scale
```

Options:
- `--session` or `-s`: Path to session folder (required)
- `--output` or `-o`: Path to output folder (default: session_folder/template_matches)
- `--method` or `-m`: OpenCV template matching method
- `--threshold` or `-t`: Matching threshold (0.0-1.0)
- `--multi-scale`: Enable multi-scale template matching
- `--debug` or `-d`: Enable debug output

## Technical Details

### Template Matching Methods

The module supports all OpenCV template matching methods:

- `cv2.TM_CCOEFF_NORMED` (Recommended): Correlation coefficient, normalized
- `cv2.TM_CCORR_NORMED`: Cross-correlation, normalized
- `cv2.TM_SQDIFF_NORMED`: Square difference, normalized
- `cv2.TM_CCOEFF`: Correlation coefficient
- `cv2.TM_CCORR`: Cross-correlation
- `cv2.TM_SQDIFF`: Square difference

For SEM images, `cv2.TM_CCOEFF_NORMED` typically gives the best results.

### Multi-Scale Matching

When multi-scale matching is enabled, the system will:

1. Estimate the appropriate scale based on the magnification ratio
2. Try multiple scales around this estimate to find the best match
3. This helps overcome differences between theoretical and actual magnification

### Integration with Metadata

The template matching works in conjunction with metadata-based containment checks:

1. First, check if metadata indicates containment
2. Then, verify visually using template matching
3. If metadata check fails but template matching succeeds, the relationship is still accepted

This dual approach improves robustness when dealing with imprecise stage position data.

## Output Files

Template matching generates several output files in the `template_matches` subfolder:

- `match_results.json`: Detailed JSON data about all matches
- `match_report.txt`: Human-readable summary report
- `match_*.png`: Visualizations of each match with bounding boxes

## Performance Considerations

Template matching is computationally intensive. For sessions with many images:

1. Processing may take several minutes
2. Enable multi-scale only when needed
3. Consider running the test script in advance to pre-compute matches

## Troubleshooting

Common issues:

1. **No matches found**: Try lowering the threshold value
2. **False positives**: Increase the threshold value
3. **Slow performance**: Disable multi-scale matching for faster results
4. **Memory errors**: Process fewer images at a time

## Examples

### Example Match Visualization

When template matching finds a match, it creates a visualization showing:

- The low magnification image with a red bounding box
- The matching score and scale factor
- The high magnification image for comparison

These visualizations help validate the containment relationships and can be included in reports.

## Future Enhancements

Planned improvements:

1. GPU acceleration for faster processing
2. Additional preprocessing options for different SEM image types
3. Interactive visualization of matches in the main application
4. Integration with other workflow types beyond MagGrid
