"""
Code Ingestion Module

Scans the codebase using AST and populates the GraphDB with code entities:
- CodeFile
- CodeClass
- CodeFunction

Usage:
    python -m app.code_ingest --root . --dry-run
    python -m app.code_ingest --root .
"""

import argparse
import ast
import logging
import os
from typing import List, Optional

from agent_jira.graphdb import graph_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("code_ingest")


class CodeVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, dry_run: bool = False):
        self.file_path = file_path
        self.dry_run = dry_run
        self.file_node_id = f"file:{file_path}"
        self.class_stack: List[str] = []

    def visit_Module(self, node: ast.Module) -> None:
        """Visita il modulo (file) principale."""
        logger.info(f"Processing File: {self.file_path}")
        if not self.dry_run:
            graph_db.upsert_code_node(
                node_id=self.file_node_id,
                label="CodeFile",
                name=os.path.basename(self.file_path),
                file_path=self.file_path,
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visita definizioni di classe."""
        class_name = node.name
        # Costruiamo un ID qualificato: file:path::ClassName
        full_name = f"{self.file_path}::{class_name}"
        node_id = f"class:{full_name}"

        logger.info(f"  Found Class: {class_name}")

        if not self.dry_run:
            graph_db.upsert_code_node(
                node_id=node_id,
                label="CodeClass",
                name=class_name,
                file_path=self.file_path,
                properties={"lineno": node.lineno},
            )
            # Link File -> Class
            graph_db.upsert_code_relation(self.file_node_id, "DEFINES", node_id)

        self.class_stack.append(node_id)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visita definizioni di funzione (o metodo)."""
        func_name = node.name
        # Se siamo dentro una classe, è un metodo
        if self.class_stack:
            parent_id = self.class_stack[-1]
            full_name = f"{parent_id}::{func_name}"
        else:
            parent_id = self.file_node_id
            full_name = f"{self.file_path}::{func_name}"

        node_id = f"func:{full_name}"

        logger.debug(f"    Found Function: {func_name} (parent: {parent_id})")

        if not self.dry_run:
            graph_db.upsert_code_node(
                node_id=node_id,
                label="CodeFunction",
                name=func_name,
                file_path=self.file_path,
                properties={"lineno": node.lineno, "is_method": bool(self.class_stack)},
            )
            # Link Parent (File or Class) -> Function
            # Se è metodo: Class -> CONTAINS -> Function
            # Se è funzione top-level: File -> DEFINES -> Function
            rel_type = "CONTAINS" if self.class_stack else "DEFINES"
            graph_db.upsert_code_relation(parent_id, rel_type, node_id)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # Treat async same as sync for now


def ingest_codebase(
    root_dir: str, dry_run: bool = False, excludes: Optional[List[str]] = None
):
    excludes = excludes or [
        ".git",
        "__pycache__",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".serena",
        "logs",
    ]

    for root, dirs, files in os.walk(root_dir):
        # Filter directories inplace
        dirs[:] = [d for d in dirs if d not in excludes]

        for file in files:
            if not file.endswith(".py"):
                continue

            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, root_dir)

            # Skip skipped dirs if relpath starts with them (double check)
            if any(part in excludes for part in relative_path.split(os.sep)):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source, filename=full_path)
                visitor = CodeVisitor(file_path=relative_path, dry_run=dry_run)
                visitor.visit(tree)

            except Exception as e:
                logger.error(f"Failed to parse {relative_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest codebase into GraphDB")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB")

    args = parser.parse_args()

    if not args.dry_run and not graph_db.is_enabled():
        logger.warning("GraphDB is disabled. Use GRAPH_DB_ENABLED=true to write.")

    ingest_codebase(args.root, args.dry_run)
