# CSV dataset ingestion

Use `/ingest path/to/dataset.csv` to add a local CSV dataset to the knowledge base. CSV files must be UTF-8 (a UTF-8 BOM is accepted), use the first row as column headers, and be no larger than 200 MiB (209,715,200 bytes). Other supported text files retain the existing 1 MB limit.

The importer streams rows rather than loading the full dataset into memory. Each non-empty row is converted into a bounded text passage such as `column: value | column: value`, then indexed for local lexical search. The existing knowledge-item limit still applies, and imported records are stored in the configured local data directory. Malformed CSV or invalid UTF-8 is rejected without adding partial rows.

This feature adds data for retrieval; it does **not** train or update a machine-learning model. ULTRON's current offline baseline has no model-training pipeline. Only import datasets you have permission to use, and do not ingest secrets or sensitive personal data.
