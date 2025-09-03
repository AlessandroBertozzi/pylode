"""Ontology fetcher that handles both URLs and local files."""

import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pylode.utils.mime_types import EXTENDED_MIME_TYPES, FORMAT_MAPPING, FILE_EXTENSIONS


class OntologyFetcher:
    """Fetches ontologies from URLs or local files with format detection."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """Initialize the fetcher with HTTP configuration.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Setup requests session with retry strategy."""
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set User-Agent similar to original Java version
        self.session.headers.update({
            'User-Agent': 'LODE Python extractor'
        })
    
    def fetch_from_url(self, url: str) -> Tuple[str, str]:
        """Fetch ontology content from URL with MIME negotiation.
        
        Args:
            url: URL to fetch from
            
        Returns:
            Tuple of (content, detected_format)
            
        Raises:
            Exception: If unable to fetch content in any supported format
        """
        errors = []
        
        # Try each MIME type in order of preference
        for mime_type in EXTENDED_MIME_TYPES:
            try:
                headers = {'Accept': mime_type}
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                
                # Detect format from Content-Type header
                content_type = response.headers.get('content-type', '').split(';')[0].strip()
                detected_format = FORMAT_MAPPING.get(content_type, self._detect_format_from_content(response.text))
                
                return response.text, detected_format
                
            except Exception as e:
                errors.append(f"MIME type {mime_type}: {str(e)}")
                continue
        
        # If all MIME types failed, try one final request without specific Accept header
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').split(';')[0].strip()
            detected_format = FORMAT_MAPPING.get(content_type, self._detect_format_from_content(response.text))
            
            return response.text, detected_format
            
        except Exception as e:
            errors.append(f"Final attempt: {str(e)}")
        
        # All attempts failed
        error_msg = "Unable to fetch ontology from URL. Errors:\n" + "\n".join(f"  - {err}" for err in errors)
        raise Exception(error_msg)
    
    def fetch_from_file(self, file_path: Path) -> Tuple[str, str]:
        """Fetch ontology content from local file.
        
        Args:
            file_path: Path to local file
            
        Returns:
            Tuple of (content, detected_format)
            
        Raises:
            Exception: If unable to read or detect format of file
        """
        if not file_path.exists():
            raise Exception(f"File does not exist: {file_path}")
        
        if not file_path.is_file():
            raise Exception(f"Path is not a file: {file_path}")
        
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Try with different encoding
                content = file_path.read_text(encoding='latin-1')
            except Exception as e:
                raise Exception(f"Unable to read file {file_path}: {e}")
        
        # Detect format from file extension
        detected_format = self._detect_format_from_extension(file_path)
        
        # If extension detection fails, try content-based detection
        if not detected_format:
            detected_format = self._detect_format_from_content(content)
        
        return content, detected_format
    
    def fetch(self, source: str) -> Tuple[str, str]:
        """Fetch ontology from URL or file path.
        
        Args:
            source: URL or file path
            
        Returns:
            Tuple of (content, detected_format)
        """
        # Check if source is a URL
        parsed = urlparse(source)
        if parsed.scheme in ('http', 'https'):
            return self.fetch_from_url(source)
        else:
            # Treat as local file path
            return self.fetch_from_file(Path(source))
    
    def _detect_format_from_extension(self, file_path: Path) -> Optional[str]:
        """Detect RDF format from file extension.
        
        Args:
            file_path: Path to check
            
        Returns:
            Detected format or None
        """
        suffix = file_path.suffix.lower()
        return FILE_EXTENSIONS.get(suffix)
    
    def _detect_format_from_content(self, content: str) -> str:
        """Detect RDF format from content analysis.
        
        Args:
            content: Content to analyze
            
        Returns:
            Detected format (defaults to 'xml')
        """
        content_lower = content.strip().lower()
        
        # Check for common RDF/XML patterns
        if (content_lower.startswith('<?xml') or 
            '<rdf:rdf' in content_lower or 
            '<owl:ontology' in content_lower or
            'xmlns:owl=' in content_lower):
            return 'xml'
        
        # Check for Turtle patterns
        if ('@prefix' in content_lower or 
            '@base' in content_lower or
            content_lower.startswith('@') or
            ' a owl:' in content_lower):
            return 'turtle'
        
        # Check for N-Triples patterns
        if ' <http' in content and ' .' in content and not '@' in content:
            return 'nt'
        
        # Check for JSON-LD patterns
        if content_lower.strip().startswith('{') and '"@context"' in content_lower:
            return 'json-ld'
        
        # Default to XML
        return 'xml'