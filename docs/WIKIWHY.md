# Use WikiWhy with ULTRON

ULTRON's `/ingest` command adds passages to its local searchable knowledge base. It does **not** train or fine-tune a language model. WikiWhy is a question-answer-explanation dataset, so importing it can help retrieval for its cause-and-effect examples; it will not make ULTRON a general-purpose trained model or guarantee more accurate answers.

## Prepare and import

From the repository root, with Python 3.10 or later:

```bash
python tools/import_wikiwhy.py
```

The script downloads the five WikiWhy v1.1 JSON files into `.wikiwhy-cache/` and writes `wikiwhy_ultron.csv`. It uses only Python's standard library. The default export is limited to 5,000 rows to match ULTRON's default knowledge capacity; use `--limit 0` to export all rows. You may select a split, for example `--split train`, or choose a destination with `--output path/to/file.csv`.

Each output row becomes one compact, labeled passage with question, cause, effect, and explanation first. Optional topic, article title, and a bounded 1,200-character context excerpt come afterward so long context text does not crowd out the answer-bearing fields. Dataset provenance is included. This layout is tailored to ULTRON's CSV row ingestion and 20,000-character passage limit.

Start ULTRON and import the CSV:

```text
/ingest wikiwhy_ultron.csv
```

ULTRON reports how many rows it imports. If you have already filled the knowledge base, its configured capacity may evict older entries. Use `/search` to check retrieval results. The dataset files are about 12 MB combined, within the CSV importer’s 200 MiB input limit.

## Dataset, attribution, and use

- Dataset: [WikiWhy](https://github.com/matt-seb-ho/WikiWhy), version 1.1, containing 9,000+ cause/effect question-answer-rationale examples.
- The generated CSV includes a source URL for provenance.
- The repository has an MIT license, but its README does not separately spell out dataset licensing terms. Review the upstream repository and dataset terms before redistribution or commercial use; this helper does not grant rights to the dataset.
- The importer fetches files from GitHub when run and caches them locally. Review the upstream data before ingesting it into your personal knowledge store.
