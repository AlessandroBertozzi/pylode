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

### Launch the command
To generate documentation for a single `.ttl` file:

```bash
pylode <input_path.ttl> -o <output_path.html>
```

### Credits
This work is based on Silvio Peroni's [LODE](https://github.com/essepuntato/LODE).
