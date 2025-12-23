# pylode
Python port of LODE (Live OWL Documentation Environment).

### Installazione
```bash
cd pylode
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Generazione Documentazione (Singolo File)
Per generare la documentazione di un singolo file `.ttl`:

```bash
pylode <input_path.ttl> -o <output_path.html>
```
**Esempio:**
```bash
pylode ../ontologies/Dataset.ttl -o ../ontologies_docs/Dataset/index.html
```

### Generazione Barch e Serializzazione
Per processare **tutti** i file `.ttl` nella cartella `../ontologies/`, generando HTML, TTL e RDF:

```bash
python scripts/serialize.py
```
Questo comando:
1. Crea una cartella per ogni ontologia in `../ontologies_docs/`
2. Genera l'`index.html`
3. Copia il file originale `.ttl`
4. Genera la serializzazione `.rdf` (RDF/XML)
