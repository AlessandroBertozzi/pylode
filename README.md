# pylode
Python port of LODE (Live OWL Documentation Environment).

### Installation
```bash
cd pylode
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Documentation Generation (Single File)
To generate documentation for a single `.ttl` file:

```bash
pylode <input_path.ttl> -o <output_path.html>
```
**Example:**
```bash
pylode ../ontologies/Dataset.ttl -o ../ontologies_docs/Dataset/index.html
```

### Batch Generation and Serialization
To process **all** `.ttl` files in the `../ontologies/` directory, generating HTML, TTL, and RDF:

```bash
python scripts/serialize.py
```
This command:
1. Creates a folder for each ontology in `../ontologies_docs/`
2. Generates the `index.html`
3. Copies the original `.ttl` file
4. Generates the `.rdf` serialization (RDF/XML)

### Credits
This work is based on Silvio Peroni's [LODE](https://github.com/essepuntato/LODE).
