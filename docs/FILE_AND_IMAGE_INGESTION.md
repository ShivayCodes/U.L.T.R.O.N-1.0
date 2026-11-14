# Importing documents and images

ULTRON's `/ingest PATH` command extracts supported local files into the searchable local knowledge base. This is retrieval-based learning: it does **not** train or update model weights.

| Format | Optional install | What is indexed |
| --- | --- | --- |
| TXT, Markdown, RST, JSON, HTML, XML, and supported source files | None | Text sections (maximum 1 MB per file) |
| CSV | None | Each non-empty row, using the first row as headers (maximum 200 MB) |
| PDF | `pip install 'ultron-1-0[pdf]'` | Extractable text, labeled by page (maximum 20 MB) |
| XLSX | `pip install 'ultron-1-0[spreadsheets]'` | Worksheet rows (first row is used as column labels; up to 10,000 rows per sheet; maximum 20 MB) |
| PNG, JPEG, BMP, GIF, TIFF, WebP | `pip install 'ultron-1-0[image-ocr]'` and install the Tesseract application | OCR-recognized text (maximum 20 MB) |

Use `/ingest path/to/file` in the CLI or GUI. Imports are stored locally in the configured data directory and can be retrieved with `/search QUERY`. Image OCR only recognizes visible text; it does not identify objects.

## Local image classification

For object/image classification, ULTRON can use an image-classification model that you have already installed locally. Install the optional runtime with `pip install 'ultron-1-0[image-classification]'`, obtain a compatible model through your normal model acquisition process, then run:

```text
/classify path/to/image.jpg path/to/local/model-directory
```

The classifier uses Transformers with `local_files_only=True`: it will not download model files. The top predictions and confidence scores are stored in local knowledge so they can be searched later. A classification score is a model prediction, not a guarantee. The optional PyTorch dependency may be large.

Files are read from local paths only. Review imported content before enabling a hosted model backend; locally stored knowledge may be included in prompts sent to that provider. Avoid importing secrets or sensitive personal data, and only use data and model weights you have permission to use.
