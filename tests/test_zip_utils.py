"""Tests for zip utility and exporter registries."""

import zipfile
from io import BytesIO

import pytest

from haytham.exporters.zip_utils import tree_to_zip


class TestTreeToZip:
    def test_creates_valid_zip(self):
        tree = {"dir/file.md": "hello", "dir/sub/other.md": "world"}
        zip_bytes = tree_to_zip(tree)
        assert isinstance(zip_bytes, bytes)
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "dir/file.md" in names
            assert "dir/sub/other.md" in names
            assert zf.read("dir/file.md").decode() == "hello"

    def test_empty_tree(self):
        zip_bytes = tree_to_zip({})
        assert isinstance(zip_bytes, bytes)
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            assert zf.namelist() == []

    def test_sorted_output(self):
        tree = {"z.md": "last", "a.md": "first"}
        zip_bytes = tree_to_zip(tree)
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            assert zf.namelist() == ["a.md", "z.md"]

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="Unsafe path"):
            tree_to_zip({"../../../etc/passwd": "malicious"})

    def test_rejects_absolute_path(self):
        with pytest.raises(ValueError, match="Unsafe path"):
            tree_to_zip({"/etc/passwd": "malicious"})


class TestExporterRegistries:
    def test_story_exporters_exist(self):
        from haytham.exporters import STORY_EXPORTERS

        assert "linear" in STORY_EXPORTERS
        assert "jira" in STORY_EXPORTERS
        assert "markdown" in STORY_EXPORTERS
        assert "csv" in STORY_EXPORTERS

    def test_project_exporters_exist(self):
        from haytham.exporters import PROJECT_EXPORTERS

        assert "openspec" in PROJECT_EXPORTERS
        assert "speckit" in PROJECT_EXPORTERS

    def test_get_exporter_still_works(self):
        from haytham.exporters import get_exporter

        exporter = get_exporter("markdown")
        assert exporter is not None

