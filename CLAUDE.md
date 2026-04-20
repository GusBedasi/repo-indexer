# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`repo-indexer` walks a local directory tree and writes per-file metadata into a SQLite database so large codebases (100GB+, millions of files) can be explored with SQL queries instead of recursive grep. The intended workflow is: run the indexer, then point any SQLite client at the resulting `<repo>_data.db` file.

## Running

```
python main.py
```

There are no dependencies — it uses only the Python 3.8+ standard library (`os.scandir`, `pathlib`, `sqlite3`, `tkinter`). On launch a Tk file dialog opens; the selected directory's basename becomes the DB filename (`<basename>_data.db`), written to the current working directory.

There is no test suite, linter config, or build step.

## Architecture

Everything lives in `main.py`. The pipeline is:

1. `walk(root)` — recursive generator over `os.scandir` that yields file `DirEntry`s, pruning directories listed in `IGNORE_DIRS` (`.git`, `node_modules`, `__pycache__`, `dist`, `build`, `webpack`, `chunks`). Symlinks are not followed.
2. `extract(entry)` — pulls path, filename, extension, language, size, mtime, line count, and depth. `line_counter` opens every file in text mode with `errors="ignore"` to count lines, so binary files are read but not decoded strictly.
3. `extract_language(extension)` — collapses extensions in `NON_CODE_EXTENSIONS` (`md`, `txt`, `json`, `yml`, `yaml`, `xml`, `csv`, `log`) to the literal string `"text"`; otherwise the extension itself is the language.
4. `init_db` — **drops and recreates** both tables on every run, so each invocation produces a fresh snapshot. Two tables:
   - `files` — flat metadata (`id`, `path`, `filename`, `language`, `line_count`, `extension`, `size`, `depth`, `modified`).
   - `file_fts` — FTS5 virtual table with a single `tokenized_path` column. `rowid` is set to the corresponding `files.id` so the two are joined via `f.id = fts.rowid`.
5. `extract_tokenized_path` — produces the FTS payload by taking the path **relative to the selected root** and replacing `/`, `.`, `_`, `-` with spaces, so FTS5's default tokenizer indexes each path segment as a word. This is what makes `MATCH 'payment'` work in place of `LIKE '%payment%'`.

Insertion is one row at a time with no batching or transaction wrapping beyond the final `conn.commit()`.

## Conventions worth preserving

- **Standard library only.** Don't introduce third-party dependencies; the README explicitly advertises a zero-install setup.
- **Fresh-snapshot semantics.** `init_db` drops tables intentionally — don't switch to incremental upserts without discussing it; downstream queries assume a clean rebuild.
- **FTS join key.** `file_fts.rowid` must equal `files.id`. Any new insert path needs to preserve this or the FTS table becomes unjoinable.
- **Path storage.** `files.path` is stored as an absolute POSIX path (`Path(...).as_posix()`); `file_fts.tokenized_path` is derived from the **relative** path. Keep both forms or queries break.
- Note: the README's "AI Use" example queries `files_fts`, but the actual table name is `file_fts` (singular). Use `file_fts` in code.
