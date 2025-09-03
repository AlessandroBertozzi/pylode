"""CLI interface for LODE using Click."""

import sys
from pathlib import Path
from typing import Optional

import click
import validators

from pylode.core.ontology_fetcher import OntologyFetcher
from pylode.core.ontology_processor import OntologyProcessor, ProcessingOptions
from pylode.core.html_generator import HTMLGenerator


@click.command()
@click.option(
    "--url",
    help="URL of the ontology to process",
    metavar="URL"
)
@click.option(
    "--file", 
    "input_file",
    type=click.Path(exists=True, path_type=Path),
    help="Local ontology file to process",
    metavar="PATH"
)
@click.option(
    "--output", 
    "-o",
    type=click.Path(path_type=Path),
    help="Output HTML file (default: stdout)",
    metavar="PATH"
)
@click.option(
    "--reasoning/--no-reasoning",
    default=False,
    help="Apply OWL reasoning (default: false)"
)
@click.option(
    "--imports/--no-imports",
    default=False,
    help="Include direct imports (default: false)"
)
@click.option(
    "--closure/--no-closure", 
    default=False,
    help="Include full import closure (default: false)"
)
@click.option(
    "--lang",
    default="en",
    type=click.Choice(["en", "fr", "it", "de"]),
    help="Output language (default: en)"
)
@click.option(
    "--format",
    "output_format",
    default="html",
    type=click.Choice(["html", "markdown"]),
    help="Output format (default: html)"
)
@click.option(
    "--css-location",
    help="Custom CSS location URL"
)
@click.option(
    "--theme",
    default="classic",
    type=click.Choice(["classic", "modern"]),
    help="HTML theme to use (default: classic)"
)
@click.version_option()
def main(
    url: Optional[str],
    input_file: Optional[Path],
    output: Optional[Path],
    reasoning: bool,
    imports: bool,
    closure: bool,
    lang: str,
    output_format: str,
    css_location: Optional[str],
    theme: str
) -> None:
    """Generate HTML documentation from OWL ontologies.
    
    Provide either --url or --file to specify the ontology source.
    
    Examples:
    
        pylode --url https://example.com/ontology.owl
        
        pylode --file ontology.owl --output docs.html
        
        pylode --url https://example.com/ontology.owl --reasoning --imports
        
        pylode --file ontology.owl --theme modern --output modern_docs.html
    """
    
    # Validate input
    if not url and not input_file:
        click.echo("Error: Must provide either --url or --file", err=True)
        sys.exit(1)
    
    if url and input_file:
        click.echo("Error: Cannot specify both --url and --file", err=True)
        sys.exit(1)
    
    if url and not validators.url(url):
        click.echo(f"Error: Invalid URL: {url}", err=True)
        sys.exit(1)
    
    try:
        # Fetch ontology content
        if url:
            click.echo(f"Fetching ontology from: {url}", err=True)
            fetcher = OntologyFetcher()
            content, detected_format = fetcher.fetch(url)
            ontology_url = url
        else:
            click.echo(f"Reading ontology from: {input_file}", err=True)
            fetcher = OntologyFetcher()
            content, detected_format = fetcher.fetch_from_file(input_file)
            ontology_url = str(input_file)
        
        # Process ontology
        click.echo("Processing ontology...", err=True)
        options = ProcessingOptions(
            use_reasoning=reasoning,
            include_imports=imports,
            include_closure=closure
        )
        
        processor = OntologyProcessor()
        graph = processor.process(content, options, ontology_url)
        
        # Generate output
        click.echo("Generating documentation...", err=True)
        generator = HTMLGenerator()
        
        if output_format == "html":
            result = generator.generate_html(
                graph=graph,
                lang=lang,
                ontology_url=ontology_url,
                css_location=css_location,
                theme=theme
            )
        else:
            result = generator.generate_markdown(
                graph=graph,
                lang=lang,
                ontology_url=ontology_url
            )
        
        # Write output
        if output:
            output.write_text(result, encoding='utf-8')
            click.echo(f"Documentation written to: {output}", err=True)
        else:
            click.echo(result)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()