# CLI direct-execution error

## Error

Running the implementation file directly, for example:

```powershell
python .\ruller_ai\cli.py
```

previously failed with an `ImportError` similar to:

```text
ImportError: attempted relative import with no known parent package
```

## Cause

`ruller_ai\cli.py` imports modules with package-relative imports (such as
`.config`). When Python runs that file by path, it does not load it as part of
the `ruller_ai` package, so those imports have no package context.

## Fix

From the repository root, run the package entry point instead:

```powershell
python -m ruller_ai
```

The CLI now detects direct execution and prints this command instead of the
confusing relative-import traceback. This preserves the package-based entry
point used by `ruller_ai\__main__.py` and the installed `ruller-ai` command.

## Related startup failure fixed

Verifying the package command exposed a separate initialization error:

```text
AttributeError: 'MemoryStore' object has no attribute 'guard_file'
```

`MemoryStore` stores the configured guard-file path as `guard_path`, but its
guard writer referenced the nonexistent `guard_file` attribute. The writer now
uses `guard_path`, allowing the documented package entry point and memory
integrity checks to work.

The guard verifier also previously accepted a readable but invalid guard
without an `expected_hash`, allowing tampered guard contents to go unnoticed.
It now rejects invalid guard data rather than silently replacing it.
