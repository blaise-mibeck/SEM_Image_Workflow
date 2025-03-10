# SEM Image Workflow Manager - Architecture Design

## 1. Architecture Overview

The application will use a layered architecture based on MVC principles, with clear separation of concerns to maintain modularity and keep files at a manageable size.

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Main Views  │  │ Controllers │  │ Workflow-specific   │  │
│  │             │  │             │  │ Views               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                           │
┌───────────────────────────┼─────────────────────────────────┐
│                           │                                 │
│             ┌─────────────▼─────────────┐                   │
│             │  Workflow Managers        │                   │
│             │  (Application Layer)      │                   │
│             └─────────────┬─────────────┘                   │
│                          │                                  │
│             ┌─────────────▼─────────────┐                   │
│             │  Domain Models            │                   │
│             │                           │                   │
│             └─────────────┬─────────────┘                   │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                           │
┌───────────────────────────┼─────────────────────────────────┐
│                           │                                 │
│             ┌─────────────▼─────────────┐                   │
│             │  Data Access Layer        │                   │
│             │                           │                   │
│             └─────────────┬─────────────┘                   │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                           │
┌───────────────────────────┼─────────────────────────────────┐
│                    File System / Data                       │
└─────────────────────────────────────────────────────────────┘
```

## 2. Project Structure

```
sem_image_manager/
│
├── main.py                # Application entry point
│
├── models/                # Domain models
│   ├── __init__.py
│   ├── session.py         # Session information model
│   ├── image_metadata.py  # SEM Image metadata model
│   ├── collection.py      # Base collection model
│   ├── workflow_models/   # Workflow-specific models
│   │   ├── __init__.py
│   │   ├── mag_grid.py
│   │   ├── mode_grid.py
│   │   ├── compare_grid.py
│   │   └── make_grid.py
│
├── views/                 # User interface
│   ├── __init__.py
│   ├── main_window.py     # Main application window
│   ├── session_panel.py   # Session information panel
│   ├── workflow_views/    # Workflow-specific views
│   │   ├── __init__.py
│   │   ├── mag_grid_view.py
│   │   ├── mode_grid_view.py
│   │   ├── compare_grid_view.py
│   │   └── make_grid_view.py
│   ├── widgets/           # Reusable UI components
│       ├── __init__.py
│       ├── image_grid.py  # Grid visualization widget
│       ├── image_selector.py
│       └── metadata_display.py
│
├── controllers/           # Application logic
│   ├── __init__.py
│   ├── session_controller.py  # Manages session data
│   ├── metadata_controller.py # Extracts & manages metadata
│   ├── workflow_controllers/  # Workflow-specific controllers
│   │   ├── __init__.py
│   │   ├── workflow_factory.py   # Creates appropriate workflow
│   │   ├── mag_grid_controller.py
│   │   ├── mode_grid_controller.py
│   │   ├── compare_grid_controller.py
│   │   └── make_grid_controller.py
│
├── data/                  # Data access layer
│   ├── __init__.py
│   ├── file_manager.py    # Handles file operations
│   ├── metadata_extractor.py  # Extracts metadata from images
│   ├── session_repository.py  # Manages session JSON persistence
│   └── exporters/        # Export functionality
│       ├── __init__.py
│       ├── grid_exporter.py  # Exports grid images
│       └── caption_generator.py  # Generates caption files
│
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── config.py          # Application configuration
│   ├── logging_utils.py   # Logging functionality
│   └── image_utils.py     # Image processing utilities
│
└── tests/                 # Unit and integration tests
    ├── __init__.py
    ├── test_models/
    ├── test_controllers/
    └── test_data/
```

## 3. Core Class Definitions

### 3.1 Domain Models

#### `Session` Class
```python
class Session:
    """Represents a SEM imaging session for one sample."""
    
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.sample_id = None
        self.sample_type = None
        self.preparation_method = None
        self.operator_name = None
        self.notes = None
        self.creation_date = None
        self.last_modified = None
        self.last_modified_by = None
        self.edit_history = []  # Track changes
        self.images = []  # List of image paths in the session
    
    def add_edit_record(self, user, field, old_value, new_value):
        """Track changes to session information."""
        pass
        
    def to_dict(self):
        """Convert session to dictionary for JSON serialization."""
        pass
        
    @classmethod
    def from_dict(cls, data, folder_path):
        """Create session from dictionary (from JSON)."""
        pass
```

#### `ImageMetadata` Class
```python
class ImageMetadata:
    """Stores and manages metadata extracted from SEM images."""
    
    def __init__(self, image_path):
        self.image_path = image_path
        self.mode = None  # SED, BSD, Topo, etc.
        self.high_voltage = None
        self.intensity = None
        self.magnification = None
        self.field_of_view_width = None
        self.field_of_view_height = None
        self.position_x = None
        self.position_y = None
        self.acquisition_date = None
        self.additional_params = {}  # Store any other metadata
    
    def is_valid(self):
        """Check if metadata has required fields."""
        pass
        
    def to_dict(self):
        """Convert metadata to dictionary for storage."""
        pass
        
    @classmethod
    def from_dict(cls, data):
        """Create metadata object from dictionary."""
        pass
```

#### Base `Collection` Class
```python
class Collection:
    """Base class for image collections in various workflows."""
    
    def __init__(self, name, workflow_type):
        self.name = name
        self.workflow_type = workflow_type
        self.images = []  # List of image paths in collection
        self.created_by = None
        self.creation_date = None
    
    def add_image(self, image_path):
        """Add image to collection."""
        pass
        
    def remove_image(self, image_path):
        """Remove image from collection."""
        pass
        
    def to_dict(self):
        """Convert collection to dictionary for storage."""
        pass
        
    @classmethod
    def from_dict(cls, data):
        """Create collection from dictionary."""
        pass
```

#### Workflow-Specific Collection Classes

```python
class MagGridCollection(Collection):
    """Collection for MagGrid workflow."""
    
    def __init__(self, name):
        super().__init__(name, "MagGrid")
        self.magnification_levels = {}  # Dict mapping magnification to images
        self.hierarchy = {}  # Dict mapping low mag image to list of higher mag images
    
    def is_valid_hierarchy(self):
        """Validate the magnification hierarchy."""
        pass
        
    def check_image_containment(self, low_mag_image, high_mag_image):
        """Check if high mag image is contained within low mag image."""
        pass
```

```python
class ModeGridCollection(Collection):
    """Collection for ModeGrid workflow."""
    
    def __init__(self, name):
        super().__init__(name, "ModeGrid")
        self.mode_map = {}  # Dict mapping modes to images
    
    def get_images_by_mode(self, mode):
        """Get all images of a specific mode."""
        pass
```

```python
class CompareGridCollection(Collection):
    """Collection for CompareGrid workflow."""
    
    def __init__(self, name):
        super().__init__(name, "CompareGrid")
        self.sample_images = {}  # Dict mapping sample IDs to images
        
    def add_sample_image(self, sample_id, image_path):
        """Add image for a specific sample."""
        pass
```

### 3.2 Data Access Layer

#### `MetadataExtractor` Class
```python
class MetadataExtractor:
    """Extracts metadata from SEM images."""
    
    def extract_metadata(self, image_path):
        """Extract metadata from image file."""
        pass
        
    def _extract_phenom_xl_metadata(self, image_path):
        """Extract metadata specific to Phenom XL format."""
        pass
```

#### `SessionRepository` Class
```python
class SessionRepository:
    """Manages persistence of session information."""
    
    def load_session(self, folder_path):
        """Load session from folder."""
        pass
        
    def save_session(self, session):
        """Save session to JSON file."""
        pass
        
    def session_exists(self, folder_path):
        """Check if session information exists."""
        pass
```

### 3.3 Controllers

#### `WorkflowFactory` Class (Factory Pattern)
```python
class WorkflowFactory:
    """Creates appropriate workflow controllers based on type."""
    
    @staticmethod
    def create_workflow(workflow_type, session):
        """Factory method to create workflow instances."""
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
```

#### Base `WorkflowController` Class
```python
class WorkflowController:
    """Base class for workflow controllers."""
    
    def __init__(self, session):
        self.session = session
        self.collections = []
        self.current_collection = None
        
    def create_collection(self, name):
        """Create a new collection."""
        pass
        
    def delete_collection(self, collection):
        """Delete a collection."""
        pass
        
    def load_collections(self):
        """Load collections from session folder."""
        pass
        
    def save_collections(self):
        """Save collections to session folder."""
        pass
        
    def export_grid(self, collection, layout, options):
        """Export grid visualization."""
        pass
        
    def generate_caption(self, collection):
        """Generate caption for the grid."""
        pass
```

### 3.4 Views

#### `MainWindow` Class
```python
class MainWindow:
    """Main application window."""
    
    def __init__(self):
        # Initialize UI components
        self.session_panel = None
        self.workflow_selector = None
        self.current_workflow_view = None
        
    def prompt_for_session(self):
        """Prompt user to select or create session."""
        pass
        
    def switch_workflow(self, workflow_type):
        """Switch to different workflow view."""
        pass
        
    def show_session_info(self, session):
        """Display session information."""
        pass
```

## 4. Design Patterns Implementation

### 4.1 Factory Pattern
The `WorkflowFactory` class demonstrates the Factory pattern, creating the appropriate workflow controller based on type. This centralizes workflow creation logic and makes adding new workflows easier.

### 4.2 Strategy Pattern
For metadata extraction, we can implement the Strategy pattern:

```python
class MetadataExtractionStrategy:
    """Base class for metadata extraction strategies."""
    
    def extract(self, image_path):
        """Extract metadata from image."""
        pass

class PhenomXLStrategy(MetadataExtractionStrategy):
    """Strategy for extracting Phenom XL metadata."""
    
    def extract(self, image_path):
        # Phenom XL specific extraction
        pass

class FutureDeviceStrategy(MetadataExtractionStrategy):
    """Strategy for extracting metadata from future devices."""
    
    def extract(self, image_path):
        # Future device specific extraction
        pass

class MetadataExtractor:
    """Uses strategies to extract metadata from images."""
    
    def __init__(self):
        self.strategies = {
            "phenomxl": PhenomXLStrategy(),
            "futuredevice": FutureDeviceStrategy()
        }
    
    def extract_metadata(self, image_path, device_type=None):
        """Extract metadata using appropriate strategy."""
        if not device_type:
            # Auto-detect device type from image
            device_type = self._detect_device_type(image_path)
            
        if device_type in self.strategies:
            return self.strategies[device_type].extract(image_path)
        else:
            raise ValueError(f"Unsupported device type: {device_type}")
            
    def _detect_device_type(self, image_path):
        """Detect device type from image characteristics."""
        # Logic to determine device type
        pass
```

### 4.3 Observer Pattern
For UI updates when data changes, we can implement the Observer pattern:

```python
class Observable:
    """Base class for objects that can be observed."""
    
    def __init__(self):
        self._observers = []
        
    def add_observer(self, observer):
        """Add an observer."""
        if observer not in self._observers:
            self._observers.append(observer)
            
    def remove_observer(self, observer):
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
            
    def notify_observers(self, *args, **kwargs):
        """Notify all observers."""
        for observer in self._observers:
            observer.update(self, *args, **kwargs)

class Observer:
    """Base class for observers."""
    
    def update(self, observable, *args, **kwargs):
        """Update method called by observable."""
        pass

# Example: Session as Observable
class Session(Observable):
    """Represents a SEM imaging session for one sample."""
    
    def __init__(self, folder_path):
        Observable.__init__(self)
        self.folder_path = folder_path
        # Other attributes as before
    
    def set_sample_id(self, sample_id, user):
        """Set sample ID and notify observers."""
        old_value = self.sample_id
        self.sample_id = sample_id
        self.add_edit_record(user, "sample_id", old_value, sample_id)
        self.notify_observers("sample_id", old_value, sample_id)

# Example: Session panel as Observer
class SessionPanel(Observer):
    """UI panel for displaying session information."""
    
    def __init__(self, session):
        self.session = session
        session.add_observer(self)
        # UI setup
        
    def update(self, observable, attribute=None, old_value=None, new_value=None):
        """Update UI when session changes."""
        if attribute == "sample_id":
            # Update sample ID display
            pass
        # Handle other attributes
```

## 5. Key Interfaces

### 5.1 Workflow Interface
Each workflow controller should implement a common interface:

```python
class WorkflowInterface:
    """Interface that all workflow controllers must implement."""
    
    def build_collections(self):
        """Build collections based on workflow criteria."""
        raise NotImplementedError
        
    def validate_collection(self, collection):
        """Validate a collection according to workflow rules."""
        raise NotImplementedError
        
    def create_grid_visualization(self, collection, layout):
        """Create grid visualization for a collection."""
        raise NotImplementedError
        
    def export_grid(self, collection, output_path):
        """Export grid visualization to file."""
        raise NotImplementedError
```

### 5.2 Grid Visualization Interface
```python
class GridVisualization:
    """Interface for grid visualization components."""
    
    def set_layout(self, rows, columns, spacing):
        """Set grid layout parameters."""
        raise NotImplementedError
        
    def add_image(self, position, image_path):
        """Add image to grid at specified position."""
        raise NotImplementedError
        
    def add_annotation(self, source_position, target_position, annotation_type):
        """Add annotation between images."""
        raise NotImplementedError
        
    def set_label(self, position, label_text):
        """Set label for image at position."""
        raise NotImplementedError
        
    def render(self):
        """Render the grid visualization."""
        raise NotImplementedError
        
    def export(self, output_path):
        """Export visualization to file."""
        raise NotImplementedError
```

## 6. Implementation Considerations

### 6.1 UI Framework
For a Windows desktop application in Python, consider:
- PyQt or PySide2 (Qt bindings) - Feature-rich, professional look
- Tkinter - Simpler, included with Python
- wxPython - Native look and feel

### 6.2 Image Processing
For image manipulation and annotation:
- PIL/Pillow - Python Imaging Library
- OpenCV - More advanced image processing capabilities

### 6.3 Data Storage
- JSON for session and collection metadata
- Consider SQLite for larger datasets if needed

### 6.4 Testing Strategy
- Unit tests for models and business logic
- Integration tests for controllers
- UI tests for workflows

### 6.5 Documentation
- Docstrings for all classes and methods
- README with setup and usage instructions
- User guide with workflow explanations

## 7. Next Steps

1. Select UI framework
2. Implement core domain models
3. Create basic file operations and metadata extraction
4. Develop UI skeleton
5. Implement workflows one by one, starting with MagGrid
6. Add export functionality
7. Implement testing
8. Create user documentation
