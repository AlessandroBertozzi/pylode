import rdflib
import re
from rdflib.namespace import RDF, RDFS, OWL, DC, DCTERMS, SKOS, XSD
from .model import OntologyMetadata, Class, Property, Individual, Element, Restriction

class OntologyParser:
    def __init__(self, source_path: str):
        self.graph = rdflib.Graph()
        self.defined_resources = set()
        try:
            self.graph.parse(source_path)
        except Exception as e:
            # Fallback for some formats or errors, or try to load as text if it's a string
            # For now assume path/url
            raise e
        
        self.ontology_node = self._find_ontology_node()
        
        # Identify all defined resources (Classes, Props, Indivs)
        defining_types = [
            OWL.Class, RDFS.Class,
            OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty,
            OWL.NamedIndividual,
            RDFS.Datatype
        ]
        for dtype in defining_types:
            for s in self.graph.subjects(RDF.type, dtype):
                if isinstance(s, rdflib.URIRef):
                    self.defined_resources.add(str(s))

    def _resolve_url(self, uri: str) -> str:
        if uri in self.defined_resources:
            return f"#{uri}"
        return uri

    def _find_ontology_node(self):
        # Look for the ?o a owl:Ontology node
        for s in self.graph.subjects(RDF.type, OWL.Ontology):
            return s
        return None

    def _is_auto_generated(self, prefix: str) -> bool:
        return bool(re.match(r"^ns\d+$", prefix))

    def _extract_preferred_and_others(self, subject, predicates) -> tuple[str | None, list[str]]:
        if not isinstance(predicates, list):
            predicates = [predicates]
        
        candidates = []
        for p in predicates:
            for o in self.graph.objects(subject, p):
                if isinstance(o, rdflib.Literal):
                    candidates.append(o)
        
        if not candidates:
            return None, []

        preferred = None
        others_literals = []

        # Find English match
        en_matches = [c for c in candidates if getattr(c, 'language', None) == 'en']
        if en_matches:
            preferred = en_matches[0]
            others_literals = [c for c in candidates if c != preferred]
        else:
            # Fallback: Prefer no language or first
            preferred = candidates[0]
            others_literals = candidates[1:]

        formatted_others = []
        for l in others_literals:
            val = str(l)
            lang = getattr(l, 'language', '')
            if lang:
                formatted_others.append(f"{val} @{lang}")
            else:
                formatted_others.append(val)
        
        return str(preferred), formatted_others

    def _get_literal(self, subject, predicates):
        pref, _ = self._extract_preferred_and_others(subject, predicates)
        return pref

    def _get_comment_with_translations(self, node):
        best, others = self._extract_preferred_and_others(node, RDFS.comment)
        if best and others:
            return best + "\n\n" + "\n".join(others)
        return best

    def _get_label_or_qname(self, subject):
        # 1. Try rdfs:label
        label = self._get_literal(subject, RDFS.label)
        if label: return label
        
        # 2. Try QName
        try:
             # compute_qname returns (prefix, namespace, name)
             # If prefix is "", it's the default namespace
             prefix, _, name = self.graph.compute_qname(subject)
             if prefix:
                 if self._is_auto_generated(prefix):
                      return str(subject)
                 return f"{prefix}:{name}"
             else:
                 # Default prefix case
                 return f":{name}" if name else str(subject)
        except Exception:
             # 3. Fallback to URI string
             return str(subject)
    
    def _get_list(self, subject, predicates):
        if not isinstance(predicates, list):
            predicates = [predicates]
        values = []
        for p in predicates:
            values.extend([self._get_label_or_qname(o) for o in self.graph.objects(subject, p)])
        return values

    def get_metadata(self) -> OntologyMetadata:
        if not self.ontology_node:
            return OntologyMetadata(uri="unknown")

        return OntologyMetadata(
            uri=str(self.ontology_node),
            title=self._get_literal(self.ontology_node, [DC.title, DCTERMS.title, RDFS.label]),
            date=self._get_literal(self.ontology_node, [DC.date, DCTERMS.date]),
            version=self._get_literal(self.ontology_node, [OWL.versionInfo]),
            creators=self._get_list(self.ontology_node, [DC.creator, DCTERMS.creator]),
            contributors=self._get_list(self.ontology_node, [DC.contributor, DCTERMS.contributor]),
            publishers=self._get_list(self.ontology_node, [DC.publisher, DCTERMS.publisher]),
            imports=self._get_list(self.ontology_node, [OWL.imports]),
            license=self._get_literal(self.ontology_node, [DC.rights, DCTERMS.rights, DCTERMS.license]),
            abstract=self._get_literal(self.ontology_node, [DCTERMS.abstract, RDFS.comment]),
            description=self._get_literal(self.ontology_node, [DC.description, DCTERMS.description])
        )

    def get_classes(self) -> list[Class]:
        classes = []
        # Classes
        for s in self.graph.subjects(RDF.type, OWL.Class):
            if isinstance(s, rdflib.BNode): continue
            classes.append(self._create_class(s))
        
        # Sort by label or URI
        return sorted(classes, key=lambda x: x.label or x.uri)

    def get_object_properties(self) -> list[Property]:
        properties = []
        for s in self.graph.subjects(RDF.type, OWL.ObjectProperty):
             if isinstance(s, rdflib.BNode): continue
             properties.append(self._create_property(s, "ObjectProperty", "op"))
        return sorted(properties, key=lambda x: x.label or x.uri)

    def get_datatype_properties(self) -> list[Property]:
        properties = []
        for s in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
             if isinstance(s, rdflib.BNode): continue
             properties.append(self._create_property(s, "DatatypeProperty", "dp"))
        return sorted(properties, key=lambda x: x.label or x.uri)

    def get_annotation_properties(self) -> list[Property]:
        properties = []
        for s in self.graph.subjects(RDF.type, OWL.AnnotationProperty):
             if isinstance(s, rdflib.BNode): continue
             properties.append(self._create_property(s, "AnnotationProperty", "ap"))
        return sorted(properties, key=lambda x: x.label or x.uri)

    def get_properties(self) -> list[Property]:
        return sorted(
            self.get_object_properties() + 
            self.get_datatype_properties() + 
            self.get_annotation_properties(), 
            key=lambda x: x.label or x.uri
        )

    def get_namespaces(self) -> list[tuple[str, str]]:
        # return list of (prefix, uri) sorted by prefix
        namespaces = []
        for prefix, uri in self.graph.namespaces():
            if prefix: # Skip empty prefix if desired, or handle it as "default"
                namespaces.append((prefix, str(uri)))
            else:
                namespaces.append(("", str(uri)))
        return sorted(namespaces, key=lambda x: x[0] or "")

    def _create_element(self, node, type_label: str = None) -> Element:
        uri_str = str(node)
        _, other_labels = self._extract_preferred_and_others(node, RDFS.label)
        return Element(
            uri=uri_str,
            label=self._get_label_or_qname(node),
            type_label=type_label,
            url=self._resolve_url(uri_str),
            other_labels=other_labels
        )

    def _create_class(self, node) -> Class:
        uri_str = str(node)
        _, other_labels = self._extract_preferred_and_others(node, RDFS.label)
        cls = Class(
            uri=uri_str,
            label=self._get_label_or_qname(node),
            comment=self._get_comment_with_translations(node),
            type_label='c',
            url=self._resolve_url(uri_str),
            other_labels=other_labels
        )
        
        # Superclasses
        for obj in self.graph.objects(node, RDFS.subClassOf):
             if isinstance(obj, rdflib.BNode): continue
             cls.super_classes.append(self._create_element(obj, 'c'))
             
        # Subclasses
        for subj in self.graph.subjects(RDFS.subClassOf, node):
             if isinstance(subj, rdflib.BNode): continue
             cls.sub_classes.append(self._create_element(subj, 'c'))
             
        # In domain of
        for subj in self.graph.subjects(RDFS.domain, node):
            if isinstance(subj, rdflib.BNode): continue
            cls.in_domain_of.append(self._create_element(subj, 'op')) # Assuming op for now, logic could be refined
            
        # In range of
        for subj in self.graph.subjects(RDFS.range, node):
            if isinstance(subj, rdflib.BNode): continue
            cls.in_range_of.append(self._create_element(subj, 'op')) # Assuming op for now

        # Members
        for subj in self.graph.subjects(RDF.type, node):
             if isinstance(subj, rdflib.BNode): continue
             # Skip if subject is a class or property itself
             if (subj, RDF.type, OWL.Class) in self.graph: continue
             cls.members.append(self._create_element(subj, 'ni'))
             
        # Disjoints
        for obj in self.graph.objects(node, OWL.disjointWith):
            if isinstance(obj, rdflib.BNode): continue
            cls.disjoint_with.append(self._create_element(obj, 'c'))
            
        # Restrictions (from subClassOf BNodes)
        for obj in self.graph.objects(node, RDFS.subClassOf):
            if isinstance(obj, rdflib.BNode):
                # Check if it's a restriction
                if (obj, RDF.type, OWL.Restriction) in self.graph:
                    restriction = self._parse_restriction(obj)
                    if restriction:
                        cls.restrictions.append(restriction)

        # SKOS properties
        for p, o in self.graph.predicate_objects(node):
            if str(p).startswith(str(SKOS)):
                 if isinstance(o, rdflib.BNode): continue # Skip complex SKOS structures for now
                 # Get label for property (e.g. skos:prefLabel)
                 prop_label = self.graph.qname(p) 
                 cls.skos_properties.append((prop_label, str(o)))

        return cls

    def _parse_restriction(self, node) -> Restriction:
        # Get onProperty
        on_prop = self.graph.value(node, OWL.onProperty)
        if not on_prop: return None
        
        # Create Element for the property
        # Try to determine if it's OP or DP or AP
        prop_type = 'op' # Default
        if (on_prop, RDF.type, OWL.DatatypeProperty) in self.graph:
            prop_type = 'dp'
        elif (on_prop, RDF.type, OWL.AnnotationProperty) in self.graph:
            prop_type = 'ap'
            
        prop_element = self._create_element(on_prop, prop_type)
        
        # someValuesFrom
        some_values = self.graph.value(node, OWL.someValuesFrom)
        if some_values:
            targets = self._get_elements_from_target(some_values)
            return Restriction(on_property=prop_element, type="some", values=targets)
            
        # allValuesFrom
        all_values = self.graph.value(node, OWL.allValuesFrom)
        if all_values:
            targets = self._get_elements_from_target(all_values)
            return Restriction(on_property=prop_element, type="only", values=targets)
            
        # hasValue
        has_value = self.graph.value(node, OWL.hasValue)
        if has_value:
             return Restriction(on_property=prop_element, type="value", literal_value=str(has_value))
             
        # Cardinality
        min_card = self.graph.value(node, OWL.minCardinality) or self.graph.value(node, OWL.minQualifiedCardinality)
        if min_card:
            return Restriction(on_property=prop_element, type="min", amount=str(min_card))
            
        max_card = self.graph.value(node, OWL.maxCardinality) or self.graph.value(node, OWL.maxQualifiedCardinality)
        if max_card:
            return Restriction(on_property=prop_element, type="max", amount=str(max_card))
            
        card = self.graph.value(node, OWL.cardinality) or self.graph.value(node, OWL.qualifiedCardinality)
        if card:
             return Restriction(on_property=prop_element, type="exactly", amount=str(card))
             
        return None

    def _get_elements_from_target(self, node) -> list[Element]:
        elements = []
        if isinstance(node, rdflib.BNode):
            # Check for Union
            union = self.graph.value(node, OWL.unionOf)
            if union:
                # UnionOf is a list structure in RDF
                current = union
                while current != RDF.nil:
                    first = self.graph.value(current, RDF.first)
                    if first:
                        elements.extend(self._get_elements_from_target(first))
                    current = self.graph.value(current, RDF.rest)
                    if not current: break
                return elements
            else:
                # Some other bnode restriction/class, fallback to 'Anonymous' or try label
                return [Element(uri=str(node), label="Anonymous", type_label="c")]
        else:
            # It's a URI node (Class or Datatype)
            # Check if it is a built-in datatype or class
            type_label = 'c'
            if str(node).startswith("http://www.w3.org/2001/XMLSchema#") or str(node).startswith("http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"):
                # It's a datatype, treat as literal-ish but we can still show it with a badge maybe?
                # Actually, standard datatypes usually don't get a 'c' badge, but let's stick to 'c' or maybe we strictly want 'c' for classes.
                # Let's check matching styles. Widoco often shows external classes with 'c' or 'ep'.
                pass
            
            # Format label/qname
            label = self._get_literal(node, RDFS.label)
            if not label:
                 try:
                    prefix, _, name = self.graph.namespace_manager.compute_qname(node)
                    if prefix: label = f"{prefix}:{name}"
                    else: label = name
                 except:
                    label = str(node)
                    
            return [Element(uri=str(node), label=label, type_label='c')]

    def _create_property(self, node, type_label, short_type) -> Property:
         uri_str = str(node)
         _, other_labels = self._extract_preferred_and_others(node, RDFS.label)
         prop = Property(
                uri=uri_str,
                label=self._get_label_or_qname(node),
                comment=self._get_comment_with_translations(node),
                type_label=short_type,
                url=self._resolve_url(uri_str),
                other_labels=other_labels
            )
            
         # Super properties
         for obj in self.graph.objects(node, RDFS.subPropertyOf):
             if isinstance(obj, rdflib.BNode): continue
             prop.super_properties.append(self._create_element(obj, short_type))
             
         # Sub properties
         for subj in self.graph.subjects(RDFS.subPropertyOf, node):
             if isinstance(subj, rdflib.BNode): continue
             prop.sub_properties.append(self._create_element(subj, short_type))

         # Domain
         for obj in self.graph.objects(node, RDFS.domain):
             if isinstance(obj, rdflib.BNode): continue
             prop.domains.append(self._create_element(obj, 'c'))
             
         # Range
         for obj in self.graph.objects(node, RDFS.range):
             if isinstance(obj, rdflib.BNode): continue
             prop.ranges.append(self._create_element(obj, 'c'))
             
         # Inverse
         for obj in self.graph.objects(node, OWL.inverseOf):
             if isinstance(obj, rdflib.BNode): continue
             prop.inverse.append(self._create_element(obj, short_type))
             
         return prop
            
    def get_named_individuals(self) -> list[Individual]:
        individuals = []
        for s in self.graph.subjects(RDF.type, OWL.NamedIndividual):
             if isinstance(s, rdflib.BNode): continue
             
             uri_str = str(s)
             _, other_labels = self._extract_preferred_and_others(s, RDFS.label)
             indiv = Individual(
                 uri=uri_str,
                 label=self._get_label_or_qname(s),
                 comment=self._get_comment_with_translations(s),
                 type_label='ni',
                 url=self._resolve_url(uri_str),
                 other_labels=other_labels
             )
             
             # Types (belongs to)
             for obj in self.graph.objects(s, RDF.type):
                 if obj == OWL.NamedIndividual: continue # Skip the generic type
                 if isinstance(obj, rdflib.BNode): continue
                 
                 indiv.types.append(self._create_element(obj, 'c'))
             
             # owl:sameAs
             for obj in self.graph.objects(s, OWL.sameAs):
                  indiv.same_as.append(str(obj))

             # Assertions (General Properties)
             # Widoco logic: exclude rdf:type, rdfs:*, dc:* (handled elsewhere)
             # We already handled label and comment.
             exclude_namespaces = [str(RDF), str(RDFS), str(DC), str(DCTERMS)]
             exclude_props = [OWL.sameAs]
             
             for p, o in self.graph.predicate_objects(s):
                 if isinstance(o, rdflib.BNode): continue # Skip BNodes for now for simplicity
                 
                 # Check exclusions
                 if p in exclude_props: continue
                 
                 ns_match = False
                 p_str = str(p)
                 for ns in exclude_namespaces:
                     if p_str.startswith(ns):
                         ns_match = True
                         break
                 if ns_match: continue
                 
                 # If we are here, it's an assertion to show
                 try:
                     prefix, _, name = self.graph.compute_qname(p)
                     if prefix and not self._is_auto_generated(prefix): prop_qname = f"{prefix}:{name}"
                     else: prop_qname = name or str(p)
                 except:
                     prop_qname = str(p)
                     
                 # Try to get label for object if it's a URI
                 obj_label = str(o)
                 obj_uri = None
                 
                 if isinstance(o, rdflib.URIRef):
                      obj_uri = self._resolve_url(str(o))
                      # Heuristic: try to get a qname for the object too if possible, or just use string
                      try:
                          op, _, oname = self.graph.compute_qname(o)
                          if op and not self._is_auto_generated(op):
                              obj_label = f"{op}:{oname}"
                      except:
                          pass

                 indiv.assertions.append((prop_qname, self._resolve_url(str(p)), obj_label, obj_uri))
             
             individuals.append(indiv)
        return sorted(individuals, key=lambda x: x.label or x.uri)
