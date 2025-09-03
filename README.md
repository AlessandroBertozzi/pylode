# PyLODE - Python Live OWL Documentation Environment

A Python CLI tool for generating beautiful HTML documentation from OWL ontologies, inspired by the original [LODE](https://github.com/essepuntato/LODE) project.

## Features

🚀 **Modern Python Implementation**
- Command-line interface with pipx support
- Multiple input sources (URLs and local files)
- Automatic RDF format detection

🎨 **Multiple Themes**
- **Classic**: Traditional LODE styling
- **Modern**: Clean design with blue/teal/orange palette
- Responsive layouts for all devices

📊 **Rich Documentation**
- Complete OWL support (classes, properties, individuals)
- Complex restriction handling (cardinality, value restrictions)
- Namespace conflict resolution with prefixes
- Multi-language support (EN, FR, IT, DE)

🔧 **Advanced Features**
- OWL reasoning with owlready2
- Import resolution and closure processing
- Multiple output formats (HTML, Markdown)
- Collapsible sidebar navigation

## Quick Start

### Installation

#### Using pipx (Recommended)
```bash
pipx install pylode
```

#### Using pip
```bash
pip install pylode
```

#### From Source
```bash
git clone <repository-url>
cd lode-python
pip install -e .
```

### Basic Usage

```bash
# Generate documentation from URL
pypylode --url https://example.com/ontology.owl

# Process local file
pypylode --file ontology.ttl --output docs.html

# Use modern theme
pypylode --file ontology.owl --theme modern --output modern_docs.html
```

## Installation Guide

### Prerequisites

- Python 3.8 or higher
- pip or pipx

### Option 1: Using pipx (Recommended)

pipx installs the tool in an isolated environment:

```bash
# Install pipx if you don't have it
pip install pipx

# Install PyLODE
pipx install pylode

# Verify installation
pylode --version
```

### Option 2: Using pip

```bash
# Install directly
pip install pylode

# Or install in a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install pylode
```

### Option 3: Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd lode-python

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Usage

### Command Line Options

```
pylode [OPTIONS]

Options:
  --url URL                     URL of the ontology to process
  --file PATH                   Local ontology file to process
  --output PATH, -o PATH        Output file (default: stdout)
  --reasoning / --no-reasoning  Apply OWL reasoning (default: false)
  --imports / --no-imports      Include direct imports (default: false)
  --closure / --no-closure      Include full import closure (default: false)
  --lang [en|fr|it|de]         Output language (default: en)
  --format [html|markdown]      Output format (default: html)
  --css-location URL            Custom CSS location URL
  --theme [classic|modern]      HTML theme (default: classic)
  --version                     Show version and exit
  --help                        Show help message
```

### Examples

#### Basic Documentation Generation

```bash
# From URL
pylode --url https://protege.stanford.edu/ontologies/pizza/pizza.owl

# From local file
pylode --file my-ontology.ttl --output documentation.html

# Output to stdout (pipe to other tools)
pylode --file ontology.owl > docs.html
```

#### Advanced Processing

```bash
# With OWL reasoning
pylode --url https://example.com/ontology.owl --reasoning --output inferred.html

# Include imports
pylode --file ontology.owl --imports --output complete.html

# Full closure with reasoning
pylode --url https://example.com/ontology.owl --closure --reasoning --output full.html
```

#### Multi-language Documentation

```bash
# French documentation
pylode --file ontology.owl --lang fr --output docs_fr.html

# Italian documentation
pylode --file ontology.owl --lang it --output docs_it.html

# German documentation  
pylode --file ontology.owl --lang de --output docs_de.html
```

#### Themes and Styling

```bash
# Modern theme
pylode --file ontology.owl --theme modern --output modern.html

# Classic theme (default)
pylode --file ontology.owl --theme classic --output classic.html

# Custom CSS location
pylode --file ontology.owl --css-location https://my-site.com/css/ --output custom.html
```

#### Markdown Output

```bash
# Generate Markdown documentation
pylode --file ontology.owl --format markdown --output README.md

# Markdown with modern theme (HTML preview)
pylode --file ontology.owl --format markdown > docs.md
```

## Supported Formats

### Input Formats

PyLODE automatically detects and supports:

- **RDF/XML** (`.rdf`, `.owl`, `.xml`)
- **Turtle** (`.ttl`, `.turtle`)
- **N-Triples** (`.nt`)
- **N-Quads** (`.nq`)
- **JSON-LD** (`.jsonld`, `.json`)
- **N3** (`.n3`)
- **TriG** (`.trig`)

### Output Formats

- **HTML**: Complete documentation with CSS styling and navigation
- **Markdown**: Clean documentation for README files or documentation sites

## Features

### Documentation Structure

Generated documentation includes:

1. **Header**: Ontology metadata, version, authors, imports
2. **Namespace Declarations**: All prefixes and namespaces used
3. **Abstract**: Ontology description and purpose
4. **Table of Contents**: Collapsible sidebar navigation
5. **Classes**: Hierarchies, restrictions, and relationships
6. **Object Properties**: Domains, ranges, and characteristics
7. **Data Properties**: Domains, ranges, and datatypes
8. **Annotation Properties**: Metadata properties
9. **Named Individuals**: Instances and their types

### Advanced OWL Support

- **Complex Restrictions**: someValuesFrom, allValuesFrom, cardinality
- **Class Expressions**: unions, intersections, complements
- **Property Chains**: Complex property relationships
- **Equivalence**: Equivalent classes and properties
- **Disjointness**: Disjoint classes and properties

### Conflict Resolution

When multiple ontologies define entities with the same name:

```
Before: Document, Document (ambiguous)
After:  foaf:Document, schema:Document (clear)
```

### Responsive Design

- **Desktop**: Full sidebar navigation with content area
- **Tablet**: Collapsible sidebar with responsive layout  
- **Mobile**: Optimized navigation and typography

## Themes

### Classic Theme
- Traditional LODE styling
- Bootstrap-inspired colors
- Professional appearance

### Modern Theme  
- Clean, contemporary design
- Blue (#2563eb), Teal (#0d9488), Orange (#f97316) palette
- Enhanced visual hierarchy
- Larger color bands for entity types

## Configuration

### Custom CSS

```bash
# Use custom CSS location
pylode --file ontology.owl --css-location https://my-domain.com/css/
```

### Environment Variables

```bash
# Set default language
export LODE_LANG=fr

# Set default theme
export LODE_THEME=modern
```

## Development

### Setup Development Environment

```bash
git clone <repository-url>
cd lode-python

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Architecture

PyLODE consists of several key components:

- **`ontology_fetcher.py`**: Handles fetching from URLs and files with format detection
- **`ontology_processor.py`**: Processes OWL ontologies using RDFLib with optional owlready2 reasoning
- **`html_generator.py`**: Generates HTML and Markdown documentation using Jinja2 templates
- **`cli.py`**: Command-line interface using Click

## Comparison with Original LODE

| Feature | Original LODE | PyLODE |
|---------|---------------|---------|
| **Platform** | Java servlet | Python CLI |
| **Installation** | Complex setup | `pipx install pylode` |
| **Input** | HTTP URLs only | URLs + local files |
| **Output** | HTML via web | HTML + Markdown files |
| **Themes** | Single style | Classic + Modern |
| **Reasoning** | Pellet reasoner | owlready2 |
| **Navigation** | Static ToC | Collapsible sidebar |
| **Mobile** | Limited | Fully responsive |
| **Conflicts** | Not handled | Automatic prefix resolution |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the original LODE project for license details.

## Author

**Alessandro Bertozzi** - bertozzi@netseven.it

Based on the original LODE project by Silvio Peroni.

## Acknowledgments

- Original LODE project: https://github.com/essepuntato/LODE
- RDFLib: https://rdflib.readthedocs.io/
- owlready2: https://owlready2.readthedocs.io/

---

**PyLODE 0.1.0-alpha** - Python Live OWL Documentation Environment