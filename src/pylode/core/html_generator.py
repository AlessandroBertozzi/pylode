"""HTML generator using Jinja2 templates."""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from jinja2 import Environment, PackageLoader, FileSystemLoader, select_autoescape
from rdflib import Graph

from pylode.core.ontology_processor import OntologyProcessor
from pylode import __version__

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 fallback
    from importlib_resources import files


class HTMLGenerator:
    """Generates HTML documentation from processed ontology data."""
    
    def __init__(self):
        """Initialize the HTML generator with Jinja2 environment."""
        # Setup Jinja2 environment with PackageLoader for installed packages
        try:
            # Try PackageLoader first (works when installed)
            self.env = Environment(
                loader=PackageLoader('lode', 'templates'),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except ModuleNotFoundError:
            # Fallback to FileSystemLoader (works during development)
            template_dir = Path(__file__).parent.parent / "templates"
            self.env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        
        # Add custom filters
        self.env.filters['uri_to_anchor'] = self._uri_to_anchor
        self.env.filters['uri_to_label'] = self._uri_to_label
        self.env.filters['get_label'] = self._get_label
        self.env.filters['get_comment'] = self._get_comment
        self.env.filters['format_restriction'] = self._format_restriction
        self.env.filters['get_unique_label'] = self._get_unique_label
        
        # Load translations
        self.translations = {}
        self._load_translations()
        
        # Load CSS files for different themes
        self.css_themes = {
            'classic': self._load_css_files(['owl.css', 'Primer.css', 'rec.css', 'extra.css']),
            'modern': self._load_css_files(['modern.css'])
        }
        
        # Load JavaScript files
        self.js_content = self._load_js_files()
    
    def _load_translations(self) -> None:
        """Load translation files."""
        try:
            # Try using importlib.resources for installed packages
            translation_files = files('lode.data.translations')
            for resource in translation_files.iterdir():
                if resource.name.endswith('.json'):
                    lang_code = resource.name[:-5]  # Remove .json extension
                    try:
                        content = resource.read_text(encoding='utf-8')
                        self.translations[lang_code] = json.loads(content)
                    except Exception as e:
                        print(f"Warning: Could not load translations for {lang_code}: {e}")
        except (ModuleNotFoundError, AttributeError):
            # Fallback to file system for development
            try:
                translations_dir = Path(__file__).parent.parent / "data" / "translations"
                for lang_file in translations_dir.glob("*.json"):
                    lang_code = lang_file.stem
                    try:
                        with open(lang_file, 'r', encoding='utf-8') as f:
                            self.translations[lang_code] = json.load(f)
                    except Exception as e:
                        print(f"Warning: Could not load translations for {lang_code}: {e}")
            except Exception as e:
                print(f"Warning: Could not load translations: {e}")
    
    def _load_css_files(self, css_files: list) -> str:
        """Load CSS files and combine them into a single string."""
        combined_css = ""
        
        try:
            # Try using importlib.resources for installed packages
            css_resources = files('lode.data.css')
            for css_file in css_files:
                try:
                    css_resource = css_resources / css_file
                    content = css_resource.read_text(encoding='utf-8')
                    combined_css += f"/* {css_file} */\n{content}\n\n"
                except Exception as e:
                    print(f"Warning: Could not load CSS file {css_file}: {e}")
        except (ModuleNotFoundError, AttributeError):
            # Fallback to file system for development
            try:
                css_dir = Path(__file__).parent.parent / "data" / "css"
                for css_file in css_files:
                    css_path = css_dir / css_file
                    if css_path.exists():
                        content = css_path.read_text(encoding='utf-8')
                        combined_css += f"/* {css_file} */\n{content}\n\n"
                    else:
                        print(f"Warning: CSS file not found: {css_path}")
            except Exception as e:
                print(f"Warning: Could not load CSS files: {e}")
        
        return combined_css
    
    def _load_js_files(self) -> str:
        """Load JavaScript files and combine them into a single string."""
        js_files = ['jquery.js', 'jquery.scrollTo.js', 'marked.min.js']
        combined_js = ""
        
        try:
            # Try using importlib.resources for installed packages
            js_resources = files('lode.data.js')
            for js_file in js_files:
                try:
                    js_resource = js_resources / js_file
                    content = js_resource.read_text(encoding='utf-8')
                    combined_js += f"/* {js_file} */\n{content}\n\n"
                except Exception as e:
                    print(f"Warning: Could not load JS file {js_file}: {e}")
        except (ModuleNotFoundError, AttributeError):
            # Fallback to file system for development
            try:
                js_dir = Path(__file__).parent.parent / "data" / "js"
                for js_file in js_files:
                    js_path = js_dir / js_file
                    if js_path.exists():
                        content = js_path.read_text(encoding='utf-8')
                        combined_js += f"/* {js_file} */\n{content}\n\n"
                    else:
                        print(f"Warning: JS file not found: {js_path}")
            except Exception as e:
                print(f"Warning: Could not load JS files: {e}")
        
        return combined_js
    
    def generate_html(
        self,
        graph: Graph,
        lang: str = "en",
        ontology_url: str = "",
        css_location: Optional[str] = None,
        theme: str = "classic"
    ) -> str:
        """Generate HTML documentation from RDF graph.
        
        Args:
            graph: Processed RDF graph
            lang: Language code for localization
            ontology_url: Original ontology URL
            css_location: Custom CSS location URL
            theme: Theme to use for styling ("classic" or "modern")
            
        Returns:
            Generated HTML content
        """
        # Process ontology data
        processor = OntologyProcessor()
        processor.graph = graph
        processor.ontology_uri = processor._find_ontology_uri(ontology_url)
        
        # Extract ontology components
        metadata = processor.get_ontology_metadata()
        classes = processor.get_classes()
        all_properties = processor.get_properties()
        individuals = processor.get_individuals()
        
        # Separate properties by type
        object_properties = {k: v for k, v in all_properties.items() if v.get('property_type') == 'object'}
        data_properties = {k: v for k, v in all_properties.items() if v.get('property_type') == 'data'}
        annotation_properties = {k: v for k, v in all_properties.items() if v.get('property_type') == 'annotation'}
        
        # Extract namespaces
        namespaces = {prefix: str(namespace) for prefix, namespace in graph.namespace_manager.namespaces()}
        
        # Detect naming conflicts and prepare unique labels
        unique_labels = self._generate_unique_labels(classes, all_properties, individuals, namespaces)
        
        # Prepare template context
        context = {
            # Ontology metadata
            'ontology_url': ontology_url,
            'ontology_title': self._get_best_label(metadata.get('title', []), metadata.get('label', []), ontology_url),
            'ontology_description': metadata.get('description', []) or metadata.get('comment', []),
            'ontology_version': self._get_first_value(metadata.get('version', [])),
            'ontology_date': self._get_first_value(metadata.get('date', [])),
            'ontology_authors': metadata.get('creator', []),
            'ontology_contributors': [],  # Could be extracted from additional properties
            'imported_ontologies': metadata.get('imports', []),
            
            # Ontology components
            'classes': classes,
            'object_properties': object_properties,
            'data_properties': data_properties,
            'annotation_properties': annotation_properties,
            'individuals': individuals,
            'namespaces': namespaces,
            
            # Configuration
            'lang': lang,
            'theme': theme,
            'css_location': css_location or self._get_default_css_location(),
            'css_content': self.css_themes.get(theme, self.css_themes['classic']),  # Theme-specific CSS
            'js_content': self.js_content,    # Inline JavaScript content
            'lode_url': 'https://github.com/essepuntato/LODE',
            'lode_version': f'PyLODE {__version__}',
            
            # Unique labels for conflict resolution
            'unique_labels': unique_labels,
        }
        
        # Add translation function
        translations = self.translations.get(lang, self.translations.get('en', {}))
        context['_'] = lambda key: translations.get(key, key)
        
        # Render template
        template = self.env.get_template('base.html')
        return template.render(**context)
    
    def generate_markdown(
        self,
        graph: Graph,
        lang: str = "en",
        ontology_url: str = ""
    ) -> str:
        """Generate Markdown documentation from RDF graph.
        
        Args:
            graph: Processed RDF graph
            lang: Language code for localization
            ontology_url: Original ontology URL
            
        Returns:
            Generated Markdown content
        """
        # Process ontology data
        processor = OntologyProcessor()
        processor.graph = graph
        processor.ontology_uri = processor._find_ontology_uri(ontology_url)
        
        metadata = processor.get_ontology_metadata()
        classes = processor.get_classes()
        all_properties = processor.get_properties()
        individuals = processor.get_individuals()
        
        # Get translations
        translations = self.translations.get(lang, self.translations.get('en', {}))
        _ = lambda key: translations.get(key, key)
        
        # Build markdown content
        lines = []
        
        # Title
        title = self._get_best_label(metadata.get('title', []), metadata.get('label', []), ontology_url)
        lines.append(f"# {title}")
        lines.append("")
        
        # Metadata
        if metadata.get('description') or metadata.get('comment'):
            lines.append("## " + _('abstract'))
            for desc in (metadata.get('description', []) or metadata.get('comment', [])):
                lines.append(desc)
            lines.append("")
        
        # Table of contents
        lines.append("## " + _('toc'))
        lines.append("")
        if classes:
            lines.append(f"- [{_('classes')}](#classes)")
        if any(p.get('property_type') == 'object' for p in all_properties.values()):
            lines.append(f"- [{_('object_properties')}](#object-properties)")
        if any(p.get('property_type') == 'data' for p in all_properties.values()):
            lines.append(f"- [{_('data_properties')}](#data-properties)")
        if individuals:
            lines.append(f"- [{_('named_individuals')}](#named-individuals)")
        lines.append("")
        
        # Classes
        if classes:
            lines.append("## " + _('classes'))
            lines.append("")
            for class_uri, class_data in sorted(classes.items()):
                label = self._get_entity_label(class_data, lang)
                lines.append(f"### {label}")
                lines.append(f"**IRI:** `{class_uri}`")
                lines.append("")
                
                comment = self._get_entity_comment(class_data, lang)
                if comment:
                    lines.append(comment)
                    lines.append("")
        
        # Object Properties
        object_props = {k: v for k, v in all_properties.items() if v.get('property_type') == 'object'}
        if object_props:
            lines.append("## " + _('object_properties'))
            lines.append("")
            for prop_uri, prop_data in sorted(object_props.items()):
                label = self._get_entity_label(prop_data, lang)
                lines.append(f"### {label}")
                lines.append(f"**IRI:** `{prop_uri}`")
                lines.append("")
                
                comment = self._get_entity_comment(prop_data, lang)
                if comment:
                    lines.append(comment)
                    lines.append("")
        
        # Data Properties
        data_props = {k: v for k, v in all_properties.items() if v.get('property_type') == 'data'}
        if data_props:
            lines.append("## " + _('data_properties'))
            lines.append("")
            for prop_uri, prop_data in sorted(data_props.items()):
                label = self._get_entity_label(prop_data, lang)
                lines.append(f"### {label}")
                lines.append(f"**IRI:** `{prop_uri}`")
                lines.append("")
                
                comment = self._get_entity_comment(prop_data, lang)
                if comment:
                    lines.append(comment)
                    lines.append("")
        
        # Named Individuals
        if individuals:
            lines.append("## " + _('named_individuals'))
            lines.append("")
            for ind_uri, ind_data in sorted(individuals.items()):
                label = self._get_entity_label(ind_data, lang)
                lines.append(f"### {label}")
                lines.append(f"**IRI:** `{ind_uri}`")
                lines.append("")
                
                comment = self._get_entity_comment(ind_data, lang)
                if comment:
                    lines.append(comment)
                    lines.append("")
        
        return "\n".join(lines)
    
    def _uri_to_anchor(self, uri: str) -> str:
        """Convert URI to HTML anchor ID."""
        # Remove protocol and clean up for anchor
        clean_uri = re.sub(r'^https?://', '', uri)
        clean_uri = re.sub(r'[^a-zA-Z0-9_-]', '_', clean_uri)
        return clean_uri
    
    def _uri_to_label(self, uri: str) -> str:
        """Convert URI to human-readable label."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def _get_label(self, entity_data: Dict[str, Any], lang: str) -> str:
        """Get label for entity in specified language."""
        return self._get_entity_label(entity_data, lang)
    
    def _get_comment(self, entity_data: Dict[str, Any], lang: str) -> Optional[str]:
        """Get comment for entity in specified language."""
        return self._get_entity_comment(entity_data, lang)
    
    def _get_unique_label(self, entity_data: Dict[str, Any], lang: str, unique_labels: Dict[str, str]) -> str:
        """Get unique label for entity, with prefix if there are conflicts."""
        if 'uri' in entity_data:
            uri = entity_data['uri']
            if uri in unique_labels:
                return unique_labels[uri]
        
        # Fallback to regular label
        return self._get_entity_label(entity_data, lang)
    
    def _get_entity_label(self, entity_data: Dict[str, Any], lang: str) -> str:
        """Get the best label for an entity."""
        labels = entity_data.get('labels', {})
        
        # Try requested language first
        if lang in labels and labels[lang]:
            return labels[lang][0]
        
        # Try English fallback
        if 'en' in labels and labels['en']:
            return labels['en'][0]
        
        # Try any available language
        for lang_labels in labels.values():
            if lang_labels:
                return lang_labels[0]
        
        # Fallback to URI fragment
        uri = entity_data.get('uri', '')
        return self._uri_to_label(uri)
    
    def _get_entity_comment(self, entity_data: Dict[str, Any], lang: str) -> Optional[str]:
        """Get the best comment for an entity."""
        comments = entity_data.get('comments', {})
        
        # Try requested language first
        if lang in comments and comments[lang]:
            return comments[lang][0]
        
        # Try English fallback
        if 'en' in comments and comments['en']:
            return comments['en'][0]
        
        # Try any available language
        for lang_comments in comments.values():
            if lang_comments:
                return lang_comments[0]
        
        return None
    
    def _get_best_label(self, titles: list, labels: list, fallback: str) -> str:
        """Get the best available title/label."""
        if titles:
            return titles[0]
        if labels:
            return labels[0]
        return self._uri_to_label(fallback)
    
    def _get_first_value(self, values: list) -> Optional[str]:
        """Get first value from list or None."""
        return values[0] if values else None
    
    def _format_restriction(self, restriction: Dict[str, Any], lang: str) -> str:
        """Format a restriction for display in HTML."""
        if not isinstance(restriction, dict) or 'type' not in restriction:
            return str(restriction)
        
        if restriction['type'] == 'restriction':
            property_label = self._uri_to_label(restriction['property'])
            value_label = self._uri_to_label(restriction['value'])
            
            restriction_type = restriction['restriction_type']
            
            if restriction_type == 'some':
                return f"<strong>{property_label}</strong> <em>some</em> {value_label}"
            elif restriction_type == 'all':
                return f"<strong>{property_label}</strong> <em>only</em> {value_label}"
            elif restriction_type == 'value':
                return f"<strong>{property_label}</strong> <em>has value</em> {value_label}"
            elif restriction_type == 'min':
                return f"<strong>{property_label}</strong> <em>min</em> {restriction['value']}"
            elif restriction_type == 'max':
                return f"<strong>{property_label}</strong> <em>max</em> {restriction['value']}"
            elif restriction_type == 'exactly':
                return f"<strong>{property_label}</strong> <em>exactly</em> {restriction['value']}"
            elif restriction_type == 'min_qualified':
                on_class = self._uri_to_label(restriction.get('on_class', ''))
                return f"<strong>{property_label}</strong> <em>min</em> {restriction['value']} {on_class}"
            elif restriction_type == 'max_qualified':
                on_class = self._uri_to_label(restriction.get('on_class', ''))
                return f"<strong>{property_label}</strong> <em>max</em> {restriction['value']} {on_class}"
            elif restriction_type == 'exactly_qualified':
                on_class = self._uri_to_label(restriction.get('on_class', ''))
                return f"<strong>{property_label}</strong> <em>exactly</em> {restriction['value']} {on_class}"
                
        elif restriction['type'] == 'union':
            members = []
            for member in restriction['members']:
                if isinstance(member, dict):
                    members.append(self._format_restriction(member, lang))
                else:
                    member_label = self._uri_to_label(str(member))
                    # Make class names bold for readability
                    members.append(f"<strong>{member_label}</strong>")
            return f"({' <em>or</em> '.join(members)})"
            
        elif restriction['type'] == 'intersection':
            members = []
            for member in restriction['members']:
                if isinstance(member, dict):
                    members.append(self._format_restriction(member, lang))
                else:
                    member_label = self._uri_to_label(str(member))
                    # Make class names bold for readability
                    members.append(f"<strong>{member_label}</strong>")
            return f"({' <em>and</em> '.join(members)})"
            
        elif restriction['type'] == 'complement':
            class_label = self._uri_to_label(restriction['class'])
            return f"<em>not</em> {class_label}"
            
        elif restriction['type'] == 'enumeration':
            members = []
            for member in restriction['members']:
                members.append(self._uri_to_label(str(member)))
            return f"{{{'}, '.join(members)}}}"
        
        return str(restriction)
    
    def _generate_unique_labels(self, classes: Dict[str, Any], properties: Dict[str, Any], individuals: Dict[str, Any], namespaces: Dict[str, str]) -> Dict[str, str]:
        """Generate unique labels for entities to resolve naming conflicts."""
        unique_labels = {}
        
        # Collect all entities
        all_entities = {}
        all_entities.update(classes)
        all_entities.update(properties) 
        all_entities.update(individuals)
        
        # Group entities by their display name
        name_groups = {}
        for uri, entity_data in all_entities.items():
            display_name = self._get_entity_label(entity_data, 'en').lower()  # Use English as base
            if display_name not in name_groups:
                name_groups[display_name] = []
            name_groups[display_name].append((uri, entity_data))
        
        # Generate unique labels for conflicting names
        for display_name, entities in name_groups.items():
            if len(entities) > 1:  # Conflict detected
                for uri, entity_data in entities:
                    # Get the prefix for this URI
                    prefix = self._get_prefix_for_uri(uri, namespaces)
                    original_label = self._get_entity_label(entity_data, 'en')
                    
                    if prefix and prefix != 'base':
                        unique_labels[uri] = f"{prefix}:{original_label}"
                    else:
                        # Fallback to namespace-based prefix
                        namespace_prefix = self._extract_namespace_prefix(uri)
                        if namespace_prefix:
                            unique_labels[uri] = f"{namespace_prefix}:{original_label}"
                        else:
                            unique_labels[uri] = original_label
            else:
                # No conflict, use original label
                uri, entity_data = entities[0]
                unique_labels[uri] = self._get_entity_label(entity_data, 'en')
        
        return unique_labels
    
    def _get_prefix_for_uri(self, uri: str, namespaces: Dict[str, str]) -> Optional[str]:
        """Find the prefix for a given URI based on registered namespaces."""
        for prefix, namespace in namespaces.items():
            if uri.startswith(namespace):
                return prefix
        return None
    
    def _extract_namespace_prefix(self, uri: str) -> Optional[str]:
        """Extract a namespace prefix from the URI itself."""
        if '#' in uri:
            namespace = uri.split('#')[0]
        elif '/' in uri:
            parts = uri.rstrip('/').split('/')
            if len(parts) > 1:
                namespace = parts[-2]  # Get second-to-last part as prefix
            else:
                return None
        else:
            return None
            
        # Clean up the namespace to make a valid prefix
        if namespace:
            namespace = namespace.replace('http://', '').replace('https://', '')
            namespace = namespace.replace('www.', '')
            parts = namespace.split('.')
            if len(parts) > 1:
                return parts[0][:8]  # First part, max 8 chars
            return namespace[:8]  # Max 8 chars
        
        return None
    
    def _get_default_css_location(self) -> str:
        """Get default CSS location."""
        # This could be configurable or point to local/remote CSS files
        return "https://lode.sourceforge.net/css/"