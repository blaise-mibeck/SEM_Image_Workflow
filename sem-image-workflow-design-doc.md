# SEM Image Workflow Manager - Design Document

## 1. Program Overview & Purpose

The SEM Image Workflow Manager is a Windows desktop application designed to organize, process, and visualize Scanning Electron Microscope (SEM) images collected during examination sessions. The program addresses the need for standardized organization of SEM session data, extraction and utilization of image metadata, and creation of specific image grid visualizations for reporting purposes.

The application enables different visualization workflows that allow operators to create meaningful comparisons and hierarchical views of SEM images, with the ultimate goal of producing high-quality figures for research reports and publications.

## 2. User Roles & Requirements

### Primary Users
- SEM operators
- Researchers analyzing SEM data
- Report writers incorporating SEM imagery

### User Authentication
- Users must enter their name when starting the program
- Changes to session information will be tracked with user attribution

## 3. Data Management

### Session Data
- **Session Information**
  - To be stored in JSON format in the session folder
  - Required fields:
    - Sample ID
    - Sample type
    - Preparation method
    - Operator name
    - Notes/comments
  - If information doesn't exist, prompt user to enter
  - If information exists, allow option to view/edit with change tracking

### Image Metadata
- **Metadata Extraction**
  - Initially supports Phenom XL SEM format
  - Extensible for future SEM equipment
  - Read from TIFF files
  - Relevant metadata includes:
    - Mode (SED, BSD, Topo, etc.)
    - High Voltage setting
    - Intensity setting
    - Field of view width and height
    - Sample position (x, y coordinates)
    - Magnification
  - Store metadata in standardized format within session folder
  - Images without proper metadata can be ignored in workflows

### Workflow Collections
- Each workflow generates collections based on specific criteria
- Collection information stored in text files within workflow-specific subfolders
- Each collection generates an exportable grid visualization

## 4. Workflow Definitions

### 4.1 MagGrid Workflow

**Purpose:** Create hierarchical visualizations of the same scene at different magnifications

**Collection Criteria:**
- Images must have the same mode, High Voltage, and intensity
- Higher magnification images must be fully contained within lower magnification images
- Uses stage position and field of view data to determine containment relationships

**Grid Visualization:**
- Layout options:
  - For 2 images: 2×1 grid (2 rows, 1 column)
  - For 3-4 images: 2×2 grid (2 rows, 2 columns)
  - For 5-6 images: 3×2 grid (3 rows, 2 columns)
- 4-pixel spacing between images
- Magnification increases from left to right, top to bottom

**Annotation Features:**
- Bounding boxes on lower magnification images showing field of higher magnification image
- Matching colored borders on higher magnification images
- Options for annotation style (on/off, dotted/solid)

**User Interaction:**
- Allow selection of which images to include in the grid
- Allow selection of alternative images at same magnification (only valid containment options)
- Updates to selected images should cascade to update all related annotations

**Export:**
- PNG format
- Naming convention: [SEM Session]_[Sample ID]_MagGrid-#.png
- Accompanying caption text file with same base name

### 4.2 ModeGrid Workflow

**Purpose:** Compare the same scene imaged with different detector modes to highlight various characteristics

**Collection Criteria:**
- Images must be of the same scene and same magnification
- Images differ in imaging modes (SED, BSD full, different Topo modes)
- Uses metadata to determine which images show the same location and field of view

**Grid Visualization:**
- Layout options similar to MagGrid
- No annotation/bounding boxes needed
- Mode information visible in image data bars

**User Interaction:**
- Allow selection of which modes to include
- Allow changing the order of images in the grid
- Default order: SED images first, followed by Topo images

**Export:**
- PNG format
- Naming convention: [SEM Session]_[Sample ID]_ModeGrid-#.png
- Accompanying caption text file with same base name

### 4.3 CompareGrid Workflow

**Purpose:** Compare different samples under similar imaging conditions

**Collection Criteria:**
- Uses images from multiple session folders (different samples)
- Images should have the same mode and similar magnification
- Exact magnification match not required, but should be close

**Grid Visualization:**
- Layout options:
  - For 2 samples: 1×2 grid (1 row, 2 columns)
  - For 3-4 samples: 2×2 grid (2 rows, 2 columns)
  - For 5-6 samples: 3×2 grid (3 rows, 2 columns)
- Sample ID displayed at the top of each image
- Text requirements: Arial font, 10pt size when image width is 6.5 inches

**User Interaction:**
- Allow selection of which images to include
- Default order based on sample ID

**Export:**
- PNG format
- Naming convention should indicate samples being compared
- Accompanying caption text file with same base name

### 4.4 MakeGrid Workflow

**Purpose:** Flexible "catch-all" option when images don't meet criteria for other workflows

**Collection Criteria:**
- No strict metadata requirements
- User manually selects images from the session folder

**Grid Visualization:**
- Layout options similar to other workflows
- No special annotations required

**User Interaction:**
- Maximum flexibility in image selection
- No automated collection grouping

**Export:**
- PNG format
- Naming convention: [SEM Session]_[Sample ID]_MakeGrid-#.png
- Accompanying caption text file with same base name

## 5. User Interface Requirements

### Main Program Interface
- Session folder selection/navigation
- User authentication (name entry)
- Session information entry/editing
- Workflow selection menu

### Per-Workflow Interfaces
- Collection browser
- Image selection interface
- Grid layout options
- Annotation controls (for MagGrid)
- Preview of grid visualization
- Export options

## 6. Input/Output Specifications

### Input
- Session folders containing SEM/EDX TIFF images
- User-provided session information
- User selections for workflow parameters

### Output
- Session information JSON file
- Metadata files
- Workflow collection files
- Grid visualization PNG exports
- Caption text files for each grid export

**Caption Files:**
- Text file with same base name as PNG export
- Contains basic description of images based on sample info and workflow type
- Assists report writers in incorporating images

## 7. Future Extensibility Considerations

- Support for additional SEM equipment types
- Additional workflow types as needed
- Integration with report generation tools
- Batch processing capabilities
- User-defined templates for grid layouts
- Remote access to SEM session folders

## 8. Error Handling and Edge Cases

- Missing or corrupt image files
- Incomplete metadata
- Invalid workflow combinations
- User permissions for file access
- Handling of large image collections
- Version control for session information changes
