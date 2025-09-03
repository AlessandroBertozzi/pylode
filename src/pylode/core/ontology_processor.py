"""Ontology processor using RDFLib and owlready2 for OWL processing."""

from dataclasses import dataclass
from typing import Optional, Set, Dict, Any
from urllib.parse import urlparse, urljoin

import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS, DC
import owlready2

from pylode.utils.mime_types import FORMAT_MAPPING


# Define common namespaces
NAMESPACES = {
    'rdf': RDF,
    'rdfs': RDFS, 
    'owl': OWL,
    'xsd': XSD,
    'dc': DC,
    'dcterms': DCTERMS,
}


@dataclass
class ProcessingOptions:
    """Options for ontology processing."""
    use_reasoning: bool = False
    include_imports: bool = False
    include_closure: bool = False
    max_import_depth: int = 10


class OntologyProcessor:
    """Processes OWL ontologies using RDFLib with optional reasoning."""
    
    def __init__(self):
        """Initialize the processor."""
        self.graph = None
        self.ontology_uri = None
        self.imported_ontologies: Set[str] = set()
    
    def process(self, content: str, options: ProcessingOptions, source_url: str = "") -> Graph:
        """Process ontology content with specified options.
        
        Args:
            content: RDF content as string
            options: Processing options
            source_url: Original source URL/path for context
            
        Returns:
            Processed RDF graph
        """
        self.graph = Graph()
        self.imported_ontologies = set()
        
        # Bind common namespaces
        for prefix, namespace in NAMESPACES.items():
            self.graph.bind(prefix, namespace)
        
        # Parse the main ontology
        try:
            # Try to detect format from content if not specified
            format_type = self._detect_format(content)
            self.graph.parse(data=content, format=format_type)
        except Exception as e:
            # Fallback: try common formats
            for fmt in ['xml', 'turtle', 'n3', 'nt']:
                try:
                    self.graph = Graph()
                    for prefix, namespace in NAMESPACES.items():
                        self.graph.bind(prefix, namespace)
                    self.graph.parse(data=content, format=fmt)
                    break
                except:
                    continue
            else:
                raise Exception(f"Unable to parse ontology content: {e}")
        
        # Find ontology URI
        self.ontology_uri = self._find_ontology_uri(source_url)
        
        # Process imports if requested
        if options.include_imports or options.include_closure:
            self._process_imports(options, source_url)
        
        # Apply reasoning if requested
        if options.use_reasoning:
            self._apply_reasoning()
        
        return self.graph
    
    def _detect_format(self, content: str) -> str:
        """Detect RDF format from content."""
        content_lower = content.strip().lower()
        
        if (content_lower.startswith('<?xml') or 
            '<rdf:rdf' in content_lower or 
            '<owl:ontology' in content_lower):
            return 'xml'
        elif ('@prefix' in content_lower or '@base' in content_lower):
            return 'turtle'
        elif content_lower.strip().startswith('{'):
            return 'json-ld'
        else:
            return 'xml'  # Default fallback
    
    def _find_ontology_uri(self, source_url: str) -> Optional[str]:
        """Find the main ontology URI from the graph."""
        # Look for owl:Ontology declarations
        for s, p, o in self.graph.triples((None, RDF.type, OWL.Ontology)):
            if isinstance(s, URIRef):
                return str(s)
        
        # Fallback: use source URL if available
        if source_url:
            parsed = urlparse(source_url)
            if parsed.scheme in ('http', 'https'):
                return source_url
        
        return None
    
    def _process_imports(self, options: ProcessingOptions, base_url: str) -> None:
        """Process ontology imports."""
        imports_to_process = set()
        
        # Find all import statements
        for s, p, o in self.graph.triples((None, OWL.imports, None)):
            if isinstance(o, URIRef):
                import_uri = str(o)
                if import_uri not in self.imported_ontologies:
                    imports_to_process.add(import_uri)
        
        # Process imports
        depth = 0
        while imports_to_process and depth < options.max_import_depth:
            current_imports = imports_to_process.copy()
            imports_to_process.clear()
            
            for import_uri in current_imports:
                try:
                    self._load_import(import_uri, base_url)
                    self.imported_ontologies.add(import_uri)
                    
                    # If processing closure, find imports in the imported ontology
                    if options.include_closure:
                        for s, p, o in self.graph.triples((None, OWL.imports, None)):
                            if isinstance(o, URIRef) and str(o) not in self.imported_ontologies:
                                imports_to_process.add(str(o))
                
                except Exception as e:
                    print(f"Warning: Could not load import {import_uri}: {e}")
            
            depth += 1
            
            # If only processing direct imports, stop after first iteration
            if not options.include_closure:
                break
    
    def _load_import(self, import_uri: str, base_url: str) -> None:
        """Load a single imported ontology."""
        from pylode.core.ontology_fetcher import OntologyFetcher
        
        # Resolve relative URIs
        if base_url and not import_uri.startswith(('http://', 'https://')):
            import_uri = urljoin(base_url, import_uri)
        
        fetcher = OntologyFetcher()
        content, format_type = fetcher.fetch_from_url(import_uri)
        
        # Parse and merge into main graph
        temp_graph = Graph()
        temp_graph.parse(data=content, format=format_type)
        
        # Add all triples to main graph
        for triple in temp_graph:
            self.graph.add(triple)
    
    def _apply_reasoning(self) -> None:
        """Apply basic OWL reasoning using owlready2."""
        try:
            # Create temporary file for owlready2
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as tmp_file:
                # Serialize graph to file
                self.graph.serialize(destination=tmp_file.name, format='xml')
                tmp_path = tmp_file.name
            
            try:
                # Load ontology with owlready2
                onto = owlready2.get_ontology(f"file://{tmp_path}").load()
                
                # Apply reasoning
                with onto:
                    owlready2.sync_reasoner(infer_property_values=True, infer_data_property_values=True)
                
                # Save reasoned ontology back to file
                onto.save(file=tmp_path, format="rdfxml")
                
                # Reload into RDFLib graph
                reasoned_graph = Graph()
                for prefix, namespace in NAMESPACES.items():
                    reasoned_graph.bind(prefix, namespace)
                reasoned_graph.parse(tmp_path, format='xml')
                
                # Replace current graph
                self.graph = reasoned_graph
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_path)
                
        except Exception as e:
            print(f"Warning: Reasoning failed: {e}")
            # Continue with original graph if reasoning fails
    
    def get_ontology_metadata(self) -> Dict[str, Any]:
        """Extract ontology metadata."""
        metadata = {}
        
        if not self.ontology_uri:
            return metadata
        
        ontology_ref = URIRef(self.ontology_uri)
        
        # Basic metadata
        for prop_name, prop_uri in [
            ('title', DC.title),
            ('description', DC.description), 
            ('creator', DC.creator),
            ('date', DC.date),
            ('version', OWL.versionInfo),
            ('comment', RDFS.comment),
            ('label', RDFS.label),
        ]:
            values = list(self.graph.objects(ontology_ref, prop_uri))
            if values:
                metadata[prop_name] = [str(v) for v in values]
        
        # Version IRI
        version_iris = list(self.graph.objects(ontology_ref, OWL.versionIRI))
        if version_iris:
            metadata['version_iri'] = str(version_iris[0])
        
        # Prior version
        prior_versions = list(self.graph.objects(ontology_ref, OWL.priorVersion))
        if prior_versions:
            metadata['prior_version'] = [str(v) for v in prior_versions]
        
        # Imports
        imports = list(self.graph.objects(ontology_ref, OWL.imports))
        if imports:
            metadata['imports'] = [str(v) for v in imports]
        
        return metadata
    
    def _process_class_expression(self, node: BNode) -> Optional[Dict[str, Any]]:
        """Process a blank node representing a class expression (restriction, union, intersection, etc.)."""
        
        # Check for OWL restrictions
        restriction_types = [
            (OWL.someValuesFrom, 'some'),
            (OWL.allValuesFrom, 'all'),
            (OWL.hasValue, 'value'),
            (OWL.minCardinality, 'min'),
            (OWL.maxCardinality, 'max'),
            (OWL.cardinality, 'exactly'),
            (OWL.minQualifiedCardinality, 'min_qualified'),
            (OWL.maxQualifiedCardinality, 'max_qualified'),
            (OWL.qualifiedCardinality, 'exactly_qualified'),
        ]
        
        for restriction_prop, restriction_type in restriction_types:
            restriction_value = list(self.graph.objects(node, restriction_prop))
            if restriction_value:
                # Get the property this restriction applies to
                on_property = list(self.graph.objects(node, OWL.onProperty))
                if on_property:
                    result = {
                        'type': 'restriction',
                        'restriction_type': restriction_type,
                        'property': str(on_property[0]) if isinstance(on_property[0], URIRef) else str(on_property[0]),
                        'value': str(restriction_value[0]) if isinstance(restriction_value[0], URIRef) else str(restriction_value[0])
                    }
                    
                    # For qualified cardinality restrictions, also get the class
                    if 'qualified' in restriction_type:
                        qualified_class = list(self.graph.objects(node, OWL.onClass))
                        if qualified_class:
                            result['on_class'] = str(qualified_class[0]) if isinstance(qualified_class[0], URIRef) else str(qualified_class[0])
                    
                    return result
        
        # Check for union/intersection/complement
        union_of = list(self.graph.objects(node, OWL.unionOf))
        if union_of:
            members = self._process_list(union_of[0])
            return {
                'type': 'union',
                'members': members
            }
            
        intersection_of = list(self.graph.objects(node, OWL.intersectionOf))
        if intersection_of:
            members = self._process_list(intersection_of[0])
            return {
                'type': 'intersection', 
                'members': members
            }
            
        complement_of = list(self.graph.objects(node, OWL.complementOf))
        if complement_of:
            return {
                'type': 'complement',
                'class': str(complement_of[0]) if isinstance(complement_of[0], URIRef) else str(complement_of[0])
            }
        
        # Check for enumeration (oneOf)
        one_of = list(self.graph.objects(node, OWL.oneOf))
        if one_of:
            members = self._process_list(one_of[0])
            return {
                'type': 'enumeration',
                'members': members
            }
        
        return None
    
    def _process_list(self, list_node) -> list:
        """Process an RDF list into a Python list."""
        members = []
        current = list_node
        
        while current and current != RDF.nil:
            # Get first element
            first = list(self.graph.objects(current, RDF.first))
            if first:
                member = first[0]
                if isinstance(member, URIRef):
                    members.append(str(member))
                elif isinstance(member, BNode):
                    # Recursively process blank nodes
                    expression = self._process_class_expression(member)
                    if expression:
                        members.append(expression)
                else:
                    members.append(str(member))
            
            # Get rest of list
            rest = list(self.graph.objects(current, RDF.rest))
            current = rest[0] if rest else None
            
        return members
    
    def _resolve_blank_node(self, bnode: BNode) -> Optional[str]:
        """Try to resolve a blank node to a meaningful description."""
        
        # Check if it has a label or comment
        labels = list(self.graph.objects(bnode, RDFS.label))
        if labels:
            return str(labels[0])
            
        comments = list(self.graph.objects(bnode, RDFS.comment))
        if comments:
            return str(comments[0])
        
        # Check if it's a class expression we can describe
        class_expression = self._process_class_expression(bnode)
        if class_expression:
            # This would be redundant since it's already in restrictions
            # But we could format it differently for annotations
            return None
        
        # Check if it has interesting properties that make it worth showing
        properties = list(self.graph.predicate_objects(bnode))
        meaningful_props = []
        
        for p, o in properties:
            # Skip structural RDF properties
            if p in [RDF.type, RDF.first, RDF.rest]:
                continue
            if isinstance(o, Literal):
                meaningful_props.append(f"{self._uri_to_label(str(p))}: {str(o)}")
            elif isinstance(o, URIRef):
                meaningful_props.append(f"{self._uri_to_label(str(p))}: {self._uri_to_label(str(o))}")
        
        if meaningful_props:
            return " | ".join(meaningful_props[:3])  # Limit to first 3 properties
            
        # If we can't resolve it meaningfully, return None to skip it
        return None
    
    def _uri_to_label(self, uri: str) -> str:
        """Convert URI to human-readable label."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def get_classes(self) -> Dict[str, Dict[str, Any]]:
        """Extract OWL classes with their properties."""
        classes = {}
        
        # Find all OWL classes
        for cls in self.graph.subjects(RDF.type, OWL.Class):
            if isinstance(cls, URIRef):
                cls_uri = str(cls)
                classes[cls_uri] = self._extract_entity_info(cls)
                
                # Add class-specific info
                superclasses = []
                restrictions = []
                
                for o in self.graph.objects(cls, RDFS.subClassOf):
                    if isinstance(o, URIRef):
                        superclasses.append(str(o))
                    elif isinstance(o, BNode):
                        # Handle complex class expressions (restrictions, etc.)
                        restriction = self._process_class_expression(o)
                        if restriction:
                            restrictions.append(restriction)
                
                classes[cls_uri]['superclasses'] = superclasses
                classes[cls_uri]['restrictions'] = restrictions
                classes[cls_uri]['subclasses'] = [
                    str(s) for s in self.graph.subjects(RDFS.subClassOf, cls)
                    if isinstance(s, URIRef)
                ]
                classes[cls_uri]['equivalent_classes'] = [
                    str(o) for o in self.graph.objects(cls, OWL.equivalentClass)
                    if isinstance(o, URIRef)
                ]
                classes[cls_uri]['disjoint_with'] = [
                    str(o) for o in self.graph.objects(cls, OWL.disjointWith)
                    if isinstance(o, URIRef)
                ]
        
        return classes
    
    def get_properties(self) -> Dict[str, Dict[str, Any]]:
        """Extract OWL properties (object and data properties)."""
        properties = {}
        
        # Object properties
        for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            if isinstance(prop, URIRef):
                prop_uri = str(prop)
                properties[prop_uri] = self._extract_property_info(prop, 'object')
        
        # Data properties  
        for prop in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            if isinstance(prop, URIRef):
                prop_uri = str(prop)
                properties[prop_uri] = self._extract_property_info(prop, 'data')
        
        # Annotation properties
        for prop in self.graph.subjects(RDF.type, OWL.AnnotationProperty):
            if isinstance(prop, URIRef):
                prop_uri = str(prop)
                properties[prop_uri] = self._extract_property_info(prop, 'annotation')
        
        return properties
    
    def get_individuals(self) -> Dict[str, Dict[str, Any]]:
        """Extract named individuals."""
        individuals = {}
        
        for ind in self.graph.subjects(RDF.type, OWL.NamedIndividual):
            if isinstance(ind, URIRef):
                ind_uri = str(ind)
                individuals[ind_uri] = self._extract_entity_info(ind)
                
                # Add individual-specific info
                individuals[ind_uri]['types'] = [
                    str(o) for o in self.graph.objects(ind, RDF.type)
                    if isinstance(o, URIRef) and str(o) != str(OWL.NamedIndividual)
                ]
        
        return individuals
    
    def _extract_entity_info(self, entity: URIRef) -> Dict[str, Any]:
        """Extract common information for any entity."""
        info = {
            'uri': str(entity),
            'labels': {},
            'comments': {},
            'annotations': []
        }
        
        # Labels (with language tags)
        for label in self.graph.objects(entity, RDFS.label):
            if isinstance(label, Literal):
                lang = label.language or 'en'
                if lang not in info['labels']:
                    info['labels'][lang] = []
                info['labels'][lang].append(str(label))
        
        # Comments (with language tags)
        for comment in self.graph.objects(entity, RDFS.comment):
            if isinstance(comment, Literal):
                lang = comment.language or 'en'
                if lang not in info['comments']:
                    info['comments'][lang] = []
                info['comments'][lang].append(str(comment))
        
        # Other annotations (filter out blank node subClassOf relationships)
        for p, o in self.graph.predicate_objects(entity):
            if p not in [RDFS.label, RDFS.comment, RDF.type]:
                # Skip blank node subClassOf relationships as they're handled as restrictions
                if p == RDFS.subClassOf and isinstance(o, BNode):
                    continue
                
                # For other blank nodes, try to resolve them or skip if they're just IDs
                if isinstance(o, BNode):
                    resolved = self._resolve_blank_node(o)
                    if resolved:
                        info['annotations'].append({
                            'property': str(p),
                            'value': resolved,
                            'type': 'resolved_bnode'
                        })
                    # Skip unresolvable blank nodes
                else:
                    info['annotations'].append({
                        'property': str(p),
                        'value': str(o),
                        'type': 'literal' if isinstance(o, Literal) else 'uri'
                    })
        
        return info
    
    def _extract_property_info(self, prop: URIRef, prop_type: str) -> Dict[str, Any]:
        """Extract property-specific information."""
        info = self._extract_entity_info(prop)
        info['property_type'] = prop_type
        
        # Domain and range
        info['domain'] = [str(o) for o in self.graph.objects(prop, RDFS.domain)]
        info['range'] = [str(o) for o in self.graph.objects(prop, RDFS.range)]
        
        # Super properties
        info['super_properties'] = [
            str(o) for o in self.graph.objects(prop, RDFS.subPropertyOf)
            if isinstance(o, URIRef)
        ]
        
        # Sub properties
        info['sub_properties'] = [
            str(s) for s in self.graph.subjects(RDFS.subPropertyOf, prop)
            if isinstance(s, URIRef)
        ]
        
        # Property characteristics (for object properties)
        if prop_type == 'object':
            info['characteristics'] = []
            if (prop, RDF.type, OWL.FunctionalProperty) in self.graph:
                info['characteristics'].append('functional')
            if (prop, RDF.type, OWL.InverseFunctionalProperty) in self.graph:
                info['characteristics'].append('inverse_functional')
            if (prop, RDF.type, OWL.TransitiveProperty) in self.graph:
                info['characteristics'].append('transitive')
            if (prop, RDF.type, OWL.SymmetricProperty) in self.graph:
                info['characteristics'].append('symmetric')
            if (prop, RDF.type, OWL.AsymmetricProperty) in self.graph:
                info['characteristics'].append('asymmetric')
            if (prop, RDF.type, OWL.ReflexiveProperty) in self.graph:
                info['characteristics'].append('reflexive')
            if (prop, RDF.type, OWL.IrreflexiveProperty) in self.graph:
                info['characteristics'].append('irreflexive')
            
            # Inverse properties
            info['inverse_of'] = [
                str(o) for o in self.graph.objects(prop, OWL.inverseOf)
                if isinstance(o, URIRef)
            ]
        
        return info