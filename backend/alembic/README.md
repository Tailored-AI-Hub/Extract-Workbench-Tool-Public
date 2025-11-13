# Alembic Migrations

This directory contains database migration scripts managed by Alembic.

## Setup

Alembic has been configured to work with the project's database models. The configuration is in `alembic.ini` and `alembic/env.py`.

## Running Migrations

### In Development
```bash
cd backend
alembic upgrade head
```

### In Docker/Production
Migrations run automatically on application startup via the lifespan function in `main.py`.

## Creating New Migrations

```bash
cd backend
alembic revision --autogenerate -m "description of changes"
```

## Current Migrations

- **001_rename_tables**: Renames old table names to match new model definitions
  - `projects` → `pdf_projects`
  - `documents` → `pdf_files`
  - `annotations` → `pdf_file_annotations`
  - And other table renames for Audio and Image models

