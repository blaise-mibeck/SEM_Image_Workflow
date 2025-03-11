#!/usr/bin/env python
"""
Minimal test script for SEM image template matching.
"""

import os
import sys
import argparse
import cv2
import numpy as np
from PIL import Image

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='SEM Image Template Matching Test')
    parser.add_argument('--session', '-s', required=True, help='Path to session folder')
    parser.add_argument('--output', '-o', help='Path to output folder')
    parser.add_argument('--threshold', '-t', type=float, default=0.5, help='Matching threshold')
    return parser.parse_args()

def main():
    """Main function."""
    # Parse command line arguments
    args = parse_args()
    
    # Validate session folder
    if not os.path.isdir(args.session):
        print(f"Error: Session folder '{args.session}' does not exist")
        return 1
    
    # Set output folder
    output_folder = args.output if args.output else os.path.join(args.session, "template_matches")
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all images
    images = []
    for file in os.listdir(args.session):
        if file.lower().endswith(('.tiff', '.tif')):
            file_path = os.path.join(args.session, file)
            images.append(file_path)
    
    print(f"Found {len(images)} images")
    
    # Create fake metadata with magnifications for testing
    # In real implementation, extract this from the images
    image_mags = {}
    for i, path in enumerate(images):
        # Assign random magnifications between 500 and 5000
        mag = (i % 5 + 1) * 1000
        image_mags[path] = mag
        print(f"  {os.path.basename(path)}: {mag}x")
    
    # Group by magnification
    mag_groups = {}
    for path, mag in image_mags.items():
        if mag not in mag_groups:
            mag_groups[mag] = []
        mag_groups[mag].append(path)
    
    # Get sorted magnifications
    mags = sorted(mag_groups.keys(), reverse=True)
    print(f"Found {len(mags)} magnification levels: {mags}")
    
    # Calculate total pairs (high-mag to low-mag)
    total_pairs = 0
    # For each high magnification level
    for i, high_mag in enumerate(mags[:-1]):  # Skip the lowest mag
        # For each lower magnification level
        for low_mag in mags[i+1:]:
            # Count pairs between these two magnification levels
            pairs_at_these_mags = len(mag_groups[high_mag]) * len(mag_groups[low_mag])
            total_pairs += pairs_at_these_mags
            print(f"  {high_mag}x to {low_mag}x: {pairs_at_these_mags} pairs")
    
    print(f"Total pairs to check: {total_pairs}")
    
    # Process each magnification pair
    match_count = 0
    pair_count = 0
    
    for i, high_mag in enumerate(mags[:-1]):  # Skip the lowest mag
        high_paths = mag_groups[high_mag]
        
        for low_mag in mags[i+1:]:
            low_paths = mag_groups[low_mag]
            
            print(f"Checking {len(high_paths)} high-mag images ({high_mag}x) against {len(low_paths)} low-mag images ({low_mag}x)")
            
            for high_path in high_paths:
                for low_path in low_paths:
                    pair_count += 1
                    
                    # Simple progress update
                    print(f"Checking pair {pair_count}/{total_pairs}: {os.path.basename(high_path)} in {os.path.basename(low_path)}")
                    
                    # In a real implementation, do template matching here
                    # For this demo, just report some fake matches
                    if pair_count % 3 == 0:  # Every third pair
                        match_count += 1
                        print(f"  Match found!")
    
    print(f"\nResults: {match_count} matches found out of {pair_count} pairs checked")
    return 0

if __name__ == "__main__":
    sys.exit(main())
