# SEM Image Workflow Manager

A desktop application for organizing and visualizing SEM (Scanning Electron Microscope) images. This application allows researchers to manage SEM session data, create grid visualizations using various workflows, and export them for reports and publications.

## Features

- **Session Management**: Track sample information, preparation methods, and other metadata
- **Metadata Extraction**: Automatically extract and utilize metadata from SEM images
- **Multiple Workflows**:
  - **MagGrid**: Create hierarchical visualizations of the same scene at different magnifications
  - **ModeGrid**: Compare the same scene imaged with different detector modes
  - **CompareGrid**: Compare different samples under similar imaging conditions
  - **MakeGrid**: Flexible manual selection for custom grids
- **Export Options**: Export grid visualizations as PNG images with accompanying caption files
- **User Tracking**: Changes to session information are tracked with user attribution

## Installation

### Prerequisites

- Python 3.8 or higher
- Required Python packages:
  - tkinter
  - Pillow (PIL)
  - tqdm (optional, for progress indication)

### Setup

1. Clone the repository or download the source code
2. Install the required dependencies:

```bash
pip install pillow tqdm
```

3. Run the application:

```bash
python launcher.py
```

## Usage

### Starting a Session

1. Launch the application
2. Enter your name when prompted
3. Select "Open Session" to open an existing session folder or "New Session" to create a new one
4. For new sessions, enter the sample information when prompted

### Working with Workflows

1. Select a workflow from the "Workflow" menu:
   - MagGrid: For hierarchical magnification visualization
   - ModeGrid: For comparing different imaging modes
   - CompareGrid: For comparing different samples
   - MakeGrid: For flexible, manual grid creation

2. For each workflow:
   - Click "Build" to automatically generate collections based on image metadata
   - Select a collection to view details and preview
   - Click "Export Grid" to generate and save the visualization

### Export Options

When exporting grids, you can specify:

- Grid layout (Auto, 2×1, 2×2, 3×2)
- Annotation style (for MagGrid: Solid, Dotted, None)
- Custom output path

## File Structure

The application maintains the following structure in session folders:

```
SessionFolder/
├── session_info.json         # Session metadata
├── MagGrid/                  # MagGrid workflow data
│   ├── collections.json      # MagGrid collections
│   └── exports/              # Exported grid images and captions
├── ModeGrid/                 # ModeGrid workflow data
│   ├── collections.json
│   └── exports/
├── CompareGrid/              # CompareGrid workflow data
│   ├── collections.json
│   └── exports/
└── MakeGrid/                 # MakeGrid workflow data
    ├── collections.json
    └── exports/
```

## Extending the Application

### Adding a New SEM Device

To add support for a new SEM device:

1. Create a new metadata extraction strategy in `data/metadata_extractor.py`
2. Implement the `extract` method to handle the specific metadata format
3. Register the strategy in the `MetadataExtractor` class

### Adding a New Workflow

To add a new workflow type:

1. Create a new collection class that extends `Collection`
2. Create a new controller class that extends `WorkflowController`
3. Register the workflow in the `WorkflowFactory` class
4. Add UI elements in the main application

## Troubleshooting

- **Missing metadata**: Ensure your SEM images contain proper metadata in the TIFF tags
- **No images found**: Check that the session folder contains valid TIFF images
- **Export errors**: Ensure you have write permissions to the export location

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Developed for improving SEM image organization and reporting
- Inspired by the needs of materials science researchers
