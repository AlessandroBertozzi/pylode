"""MIME types for RDF formats, mirroring the Java MimeType interface."""

MIME_TYPES = [
    "application/rdf+xml",
    "text/turtle",
    "application/x-turtle", 
    "text/xml",
    "text/plain",
    "*/*"
]

# Extended MIME types for better coverage
EXTENDED_MIME_TYPES = [
    "application/rdf+xml",
    "text/turtle",
    "application/x-turtle",
    "application/turtle",
    "text/n3",
    "application/n-triples",
    "text/n-triples",
    "application/n-quads", 
    "application/trig",
    "application/ld+json",
    "text/xml",
    "application/xml",
    "text/plain",
    "*/*"
]

# Format mapping for RDFLib
FORMAT_MAPPING = {
    "application/rdf+xml": "xml",
    "text/xml": "xml", 
    "application/xml": "xml",
    "text/turtle": "turtle",
    "application/x-turtle": "turtle",
    "application/turtle": "turtle",
    "text/n3": "n3",
    "application/n-triples": "nt",
    "text/n-triples": "nt",
    "application/n-quads": "nquads",
    "application/trig": "trig",
    "application/ld+json": "json-ld",
    "text/plain": "turtle"  # Default fallback
}

# File extension to format mapping
FILE_EXTENSIONS = {
    ".owl": "xml",
    ".rdf": "xml", 
    ".xml": "xml",
    ".ttl": "turtle",
    ".turtle": "turtle",
    ".n3": "n3",
    ".nt": "nt",
    ".nq": "nquads",
    ".trig": "trig",
    ".jsonld": "json-ld",
    ".json": "json-ld"
}