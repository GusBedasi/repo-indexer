# repo-indexer

indexes a local codebase into a SQLite database so you can query it instead of grepping through thousands of files.

## why

i wanted a way to understand large codebases (think 100GB, millions of files) without opening every file. Since files carry information and directory structure basically *is* the architecture, so i built a tool that walks a repo, extracts metadata, and dumps it into SQLite where i can run whatever queries i want.

## what it does

- recursively walks a directory tree (skipping `.git`, `node_modules`, etc.)
- extracts metadata per file: path, filename, extension, language, size, line count, depth, last modified
- full-text search via FTS5 — paths are tokenized (split on `/`, `.`, `_`, `-`) and stored in an inverted index, so keyword lookups use `MATCH` instead of `LIKE '%keyword%'`
- stores everything in a SQLite database
- pops up a folder picker so you don't have to type paths

## usage

```
python main.py
```

A file dialog opens, pick the repo root. it walks the tree, extracts metadata, and writes to `base_name_ + data.db`.

<details>
  <summary>Dialog window</summary>

  ![Dialog window](./assets/dialog.png)
</details>

then open the database with any SQLite client and go wild:

```sql
-- what languages make up this codebase?
SELECT language, COUNT(*) as files, SUM(line_count) as total_lines
FROM files
GROUP BY language
ORDER BY total_lines DESC;

-- biggest files
SELECT filename, line_count, size
FROM files
ORDER BY line_count DESC
LIMIT 10;

-- find files related to payments (uses FTS5 inverted index)
SELECT f.path, f.line_count
FROM file_fts fts
JOIN files f ON f.id = fts.rowid
WHERE fts.tokenized_path MATCH 'payment';

-- combine keywords (AND by default)
SELECT f.path, f.line_count
FROM file_fts fts
JOIN files f ON f.id = fts.rowid
WHERE fts.tokenized_path MATCH 'cache test';

-- what's the deepest nested file?
SELECT path, depth
FROM files
ORDER BY depth DESC
LIMIT 5;
```

## requirements

python 3.8+ (uses `os.scandir`, `pathlib`, `tkinter` — all standard library, no pip installs needed)

## what's next

- [ ] query CLI so you don't need a separate SQLite client