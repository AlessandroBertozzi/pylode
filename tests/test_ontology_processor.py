"""Tests for ontology processor module."""

import pytest
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from lode.core.ontology_processor import OntologyProcessor, ProcessingOptions


class TestOntologyProcessor:
    """Test cases for OntologyProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = OntologyProcessor()
    
    def test_detect_format_xml(self):
        """Test XML format detection."""
        xml_content = '<?xml version="1.0"?><rdf:RDF></rdf:RDF>'
        assert self.processor._detect_format(xml_content) == 'xml'
    
    def test_detect_format_turtle(self):
        """Test Turtle format detection."""
        turtle_content = '@prefix owl: <http://www.w3.org/2002/07/owl#> .'
        assert self.processor._detect_format(turtle_content) == 'turtle'
    
    def test_detect_format_jsonld(self):
        """Test JSON-LD format detection."""
        jsonld_content = '{"@context": {}}'
        assert self.processor._detect_format(jsonld_content) == 'json-ld'
    
    def test_process_basic_ontology(self):
        """Test processing a basic ontology."""
        # Create basic OWL ontology in Turtle format
        turtle_content = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix ex: <http://example.org/> .
        
        ex:ontology a owl:Ontology ;
            rdfs:label "Test Ontology" .
        
        ex:Person a owl:Class ;
            rdfs:label "Person" ;
            rdfs:comment "A human being" .
        
        ex:hasName a owl:DatatypeProperty ;
            rdfs:label "has name" ;
            rdfs:domain ex:Person .
        """
        
        options = ProcessingOptions()
        graph = self.processor.process(turtle_content, options)
        
        # Verify graph contains expected triples
        assert len(graph) > 0
        
        # Check for ontology declaration
        ex = Namespace("http://example.org/")
        assert (ex.ontology, RDF.type, OWL.Ontology) in graph
        
        # Check for class declaration
        assert (ex.Person, RDF.type, OWL.Class) in graph
    
    def test_find_ontology_uri(self):
        """Test ontology URI detection."""
        # Create graph with ontology declaration
        graph = Graph()
        ex = Namespace("http://example.org/")
        graph.add((ex.ontology, RDF.type, OWL.Ontology))
        
        self.processor.graph = graph
        uri = self.processor._find_ontology_uri("")
        
        assert uri == str(ex.ontology)
    
    def test_get_ontology_metadata(self):
        """Test metadata extraction."""
        # Create graph with metadata
        graph = Graph()
        ex = Namespace("http://example.org/")
        from rdflib.namespace import DC
        
        graph.add((ex.ontology, RDF.type, OWL.Ontology))
        graph.add((ex.ontology, DC.title, Literal("Test Ontology")))
        graph.add((ex.ontology, DC.description, Literal("A test ontology")))
        graph.add((ex.ontology, OWL.versionInfo, Literal("1.0")))
        
        self.processor.graph = graph
        self.processor.ontology_uri = str(ex.ontology)
        
        metadata = self.processor.get_ontology_metadata()
        
        assert "title" in metadata
        assert "Test Ontology" in metadata["title"]
        assert "description" in metadata
        assert "A test ontology" in metadata["description"]
        assert "version" in metadata
        assert "1.0" in metadata["version"]
    
    def test_get_classes(self):
        """Test class extraction."""
        # Create graph with classes
        graph = Graph()
        ex = Namespace("http://example.org/")
        
        graph.add((ex.Person, RDF.type, OWL.Class))
        graph.add((ex.Person, RDFS.label, Literal("Person")))
        graph.add((ex.Person, RDFS.comment, Literal("A human being")))
        
        graph.add((ex.Student, RDF.type, OWL.Class))
        graph.add((ex.Student, RDFS.subClassOf, ex.Person))
        
        self.processor.graph = graph
        classes = self.processor.get_classes()
        
        assert str(ex.Person) in classes
        assert str(ex.Student) in classes
        
        person_data = classes[str(ex.Person)]
        assert "labels" in person_data
        assert "en" in person_data["labels"]
        assert "Person" in person_data["labels"]["en"]
        
        student_data = classes[str(ex.Student)]
        assert str(ex.Person) in student_data["superclasses"]
    
    def test_get_properties(self):
        """Test property extraction."""
        # Create graph with properties
        graph = Graph()
        ex = Namespace("http://example.org/")
        
        # Object property
        graph.add((ex.knows, RDF.type, OWL.ObjectProperty))
        graph.add((ex.knows, RDFS.label, Literal("knows")))
        graph.add((ex.knows, RDFS.domain, ex.Person))
        graph.add((ex.knows, RDFS.range, ex.Person))
        
        # Data property
        graph.add((ex.hasAge, RDF.type, OWL.DatatypeProperty))
        graph.add((ex.hasAge, RDFS.label, Literal("has age")))
        graph.add((ex.hasAge, RDFS.domain, ex.Person))
        
        self.processor.graph = graph
        properties = self.processor.get_properties()
        
        assert str(ex.knows) in properties
        assert str(ex.hasAge) in properties
        
        knows_data = properties[str(ex.knows)]
        assert knows_data["property_type"] == "object"
        assert str(ex.Person) in knows_data["domain"]
        assert str(ex.Person) in knows_data["range"]
        
        age_data = properties[str(ex.hasAge)]
        assert age_data["property_type"] == "data"
    
    def test_get_individuals(self):
        """Test individual extraction."""
        # Create graph with individuals
        graph = Graph()
        ex = Namespace("http://example.org/")
        
        graph.add((ex.john, RDF.type, OWL.NamedIndividual))
        graph.add((ex.john, RDF.type, ex.Person))
        graph.add((ex.john, RDFS.label, Literal("John Doe")))
        
        self.processor.graph = graph
        individuals = self.processor.get_individuals()
        
        assert str(ex.john) in individuals
        
        john_data = individuals[str(ex.john)]
        assert str(ex.Person) in john_data["types"]
        assert "labels" in john_data
        assert "en" in john_data["labels"]
        assert "John Doe" in john_data["labels"]["en"]