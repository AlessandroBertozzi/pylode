"""Tests for ontology fetcher module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from lode.core.ontology_fetcher import OntologyFetcher


class TestOntologyFetcher:
    """Test cases for OntologyFetcher."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.fetcher = OntologyFetcher()
    
    def test_detect_format_from_content_xml(self):
        """Test XML format detection."""
        xml_content = '<?xml version="1.0"?><rdf:RDF xmlns:owl="http://www.w3.org/2002/07/owl#"></rdf:RDF>'
        format_type = self.fetcher._detect_format_from_content(xml_content)
        assert format_type == 'xml'
    
    def test_detect_format_from_content_turtle(self):
        """Test Turtle format detection."""
        turtle_content = '@prefix owl: <http://www.w3.org/2002/07/owl#> .'
        format_type = self.fetcher._detect_format_from_content(turtle_content)
        assert format_type == 'turtle'
    
    def test_detect_format_from_content_ntriples(self):
        """Test N-Triples format detection."""
        nt_content = '<http://example.org/ont> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Ontology> .'
        format_type = self.fetcher._detect_format_from_content(nt_content)
        assert format_type == 'nt'
    
    def test_detect_format_from_content_jsonld(self):
        """Test JSON-LD format detection."""
        jsonld_content = '{"@context": "http://www.w3.org/ns/owl#"}'
        format_type = self.fetcher._detect_format_from_content(jsonld_content)
        assert format_type == 'json-ld'
    
    def test_detect_format_from_extension(self):
        """Test format detection from file extension."""
        # Test various extensions
        assert self.fetcher._detect_format_from_extension(Path('test.owl')) == 'xml'
        assert self.fetcher._detect_format_from_extension(Path('test.ttl')) == 'turtle'
        assert self.fetcher._detect_format_from_extension(Path('test.nt')) == 'nt'
        assert self.fetcher._detect_format_from_extension(Path('test.jsonld')) == 'json-ld'
        assert self.fetcher._detect_format_from_extension(Path('test.unknown')) is None
    
    @patch('requests.Session.get')
    def test_fetch_from_url_success(self, mock_get):
        """Test successful URL fetching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<?xml version="1.0"?><owl:Ontology xmlns:owl="http://www.w3.org/2002/07/owl#"/>'
        mock_response.headers = {'content-type': 'application/rdf+xml'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        content, format_type = self.fetcher.fetch_from_url('http://example.org/ontology.owl')
        
        assert content.startswith('<?xml')
        assert format_type == 'xml'
        mock_get.assert_called_once()
    
    def test_fetch_from_file_success(self, tmp_path):
        """Test successful file fetching."""
        # Create test file
        test_file = tmp_path / "test.owl"
        test_content = '<?xml version="1.0"?><owl:Ontology xmlns:owl="http://www.w3.org/2002/07/owl#"/>'
        test_file.write_text(test_content, encoding='utf-8')
        
        content, format_type = self.fetcher.fetch_from_file(test_file)
        
        assert content == test_content
        assert format_type == 'xml'
    
    def test_fetch_from_file_not_found(self):
        """Test file not found error."""
        with pytest.raises(Exception, match="File does not exist"):
            self.fetcher.fetch_from_file(Path("/nonexistent/file.owl"))
    
    def test_fetch_url_detection(self):
        """Test URL vs file path detection."""
        with patch.object(self.fetcher, 'fetch_from_url') as mock_url:
            mock_url.return_value = ('content', 'xml')
            self.fetcher.fetch('http://example.org/ontology.owl')
            mock_url.assert_called_once()
        
        with patch.object(self.fetcher, 'fetch_from_file') as mock_file:
            mock_file.return_value = ('content', 'xml')
            self.fetcher.fetch('/path/to/ontology.owl')
            mock_file.assert_called_once()