"""Tests for HTML generator module."""

import pytest
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, DC

from lode.core.html_generator import HTMLGenerator


class TestHTMLGenerator:
    """Test cases for HTMLGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = HTMLGenerator()
    
    def test_uri_to_anchor(self):
        """Test URI to anchor conversion."""
        uri = "http://example.org/ontology#Person"
        anchor = self.generator._uri_to_anchor(uri)
        assert anchor == "example_org_ontology_Person"
    
    def test_uri_to_label(self):
        """Test URI to label conversion."""
        # Fragment-based URI
        uri1 = "http://example.org/ontology#Person"
        assert self.generator._uri_to_label(uri1) == "Person"
        
        # Path-based URI
        uri2 = "http://example.org/ontology/Person"
        assert self.generator._uri_to_label(uri2) == "Person"
        
        # Simple URI
        uri3 = "Person"
        assert self.generator._uri_to_label(uri3) == "Person"
    
    def test_get_entity_label(self):
        """Test entity label extraction."""
        entity_data = {
            "uri": "http://example.org/Person",
            "labels": {
                "en": ["Person"],
                "fr": ["Personne"],
                "it": ["Persona"]
            }
        }
        
        # Test language-specific label
        assert self.generator._get_entity_label(entity_data, "fr") == "Personne"
        assert self.generator._get_entity_label(entity_data, "en") == "Person"
        
        # Test fallback to English
        assert self.generator._get_entity_label(entity_data, "de") == "Person"
        
        # Test fallback to URI when no labels
        entity_no_labels = {"uri": "http://example.org/Person", "labels": {}}
        assert self.generator._get_entity_label(entity_no_labels, "en") == "Person"
    
    def test_get_entity_comment(self):
        """Test entity comment extraction."""
        entity_data = {
            "comments": {
                "en": ["A human being"],
                "fr": ["Un être humain"]
            }
        }
        
        # Test language-specific comment
        assert self.generator._get_entity_comment(entity_data, "en") == "A human being"
        assert self.generator._get_entity_comment(entity_data, "fr") == "Un être humain"
        
        # Test fallback to English
        assert self.generator._get_entity_comment(entity_data, "de") == "A human being"
        
        # Test no comment available
        entity_no_comments = {"comments": {}}
        assert self.generator._get_entity_comment(entity_no_comments, "en") is None
    
    def test_generate_html_basic(self):
        """Test basic HTML generation."""
        # Create basic ontology graph
        graph = Graph()
        ex = Namespace("http://example.org/")
        
        # Add ontology metadata
        graph.add((ex.ontology, RDF.type, OWL.Ontology))
        graph.add((ex.ontology, DC.title, Literal("Test Ontology")))
        graph.add((ex.ontology, DC.description, Literal("A test ontology")))
        
        # Add a class
        graph.add((ex.Person, RDF.type, OWL.Class))
        graph.add((ex.Person, RDFS.label, Literal("Person", lang="en")))
        graph.add((ex.Person, RDFS.comment, Literal("A human being", lang="en")))
        
        # Generate HTML
        html = self.generator.generate_html(
            graph=graph,
            lang="en",
            ontology_url="http://example.org/ontology"
        )
        
        # Verify HTML contains expected content
        assert "<!DOCTYPE html>" in html
        assert "Test Ontology" in html
        assert "A test ontology" in html
        assert "Person" in html
        assert "A human being" in html
        assert "Classes" in html or "classes" in html
    
    def test_generate_markdown_basic(self):
        """Test basic Markdown generation."""
        # Create basic ontology graph
        graph = Graph()
        ex = Namespace("http://example.org/")
        
        # Add ontology metadata
        graph.add((ex.ontology, RDF.type, OWL.Ontology))
        graph.add((ex.ontology, DC.title, Literal("Test Ontology")))
        graph.add((ex.ontology, DC.description, Literal("A test ontology")))
        
        # Add a class
        graph.add((ex.Person, RDF.type, OWL.Class))
        graph.add((ex.Person, RDFS.label, Literal("Person", lang="en")))
        graph.add((ex.Person, RDFS.comment, Literal("A human being", lang="en")))
        
        # Generate Markdown
        markdown = self.generator.generate_markdown(
            graph=graph,
            lang="en",
            ontology_url="http://example.org/ontology"
        )
        
        # Verify Markdown contains expected content
        assert "# Test Ontology" in markdown
        assert "A test ontology" in markdown
        assert "## Classes" in markdown or "## classes" in markdown
        assert "### Person" in markdown
        assert "A human being" in markdown
        assert "**IRI:**" in markdown
    
    def test_translations_loading(self):
        """Test that translations are loaded properly."""
        # Check that English translations are loaded
        assert "en" in self.generator.translations
        assert "title" in self.generator.translations["en"]
        
        # Check that other languages are loaded if files exist
        if "fr" in self.generator.translations:
            assert "title" in self.generator.translations["fr"]
    
    def test_get_best_label(self):
        """Test best label selection."""
        # Test with title available
        titles = ["My Ontology"]
        labels = ["Another Label"]
        fallback = "http://example.org/ontology"
        
        result = self.generator._get_best_label(titles, labels, fallback)
        assert result == "My Ontology"
        
        # Test with only labels
        result = self.generator._get_best_label([], labels, fallback)
        assert result == "Another Label"
        
        # Test with fallback
        result = self.generator._get_best_label([], [], fallback)
        assert result == "ontology"