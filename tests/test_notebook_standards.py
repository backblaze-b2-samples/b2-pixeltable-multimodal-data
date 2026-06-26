import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "01-video-frames-b2.ipynb"


class NotebookStandardsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.code_cells = [
            "".join(cell.get("source", []))
            for cell in cls.nb["cells"]
            if cell.get("cell_type") == "code"
        ]

    def test_dependency_install_cell_uses_locked_requirements(self):
        install_cells = [
            (index, source)
            for index, source in enumerate(self.code_cells)
            if "%pip install" in source
        ]
        self.assertEqual(len(install_cells), 1)

        install_index, install_source = install_cells[0]
        self.assertIn("requirements.lock", install_source)
        self.assertIn("--require-hashes", install_source)
        self.assertNotRegex(install_source, r"\s-(?:U|-upgrade)\b")

        setup_indexes = [
            index
            for index, source in enumerate(self.code_cells)
            if "create_b2_s3_client" in source
        ]
        self.assertTrue(setup_indexes)
        self.assertLess(install_index, setup_indexes[0])

    def test_project_metadata_constrains_boto_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("boto3>=1.43.36,<1.44", pyproject)
        self.assertIn("botocore>=1.43.36,<1.44", pyproject)

    def test_lock_export_pins_boto_dependencies(self):
        requirements_lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")

        self.assertIn("boto3==1.43.36", requirements_lock)
        self.assertIn("botocore==1.43.36", requirements_lock)
        self.assertIn("--hash=sha256:", requirements_lock)
        self.assertNotIn("--no-hashes", requirements_lock)

    def test_b2_setup_preflights_before_computed_columns(self):
        setup_indexes = [
            index
            for index, source in enumerate(self.code_cells)
            if "preflight_b2_bucket" in source
        ]
        computed_column_indexes = [
            index
            for index, source in enumerate(self.code_cells)
            if ".add_computed_column(" in source
        ]

        self.assertTrue(setup_indexes)
        self.assertTrue(computed_column_indexes)
        self.assertLess(setup_indexes[0], min(computed_column_indexes))

    def test_notebook_install_cells_do_not_bypass_locked_path(self):
        for source in self.code_cells:
            for line in source.splitlines():
                if "pip install" not in line:
                    continue
                self.assertIn("requirements.lock", line)
                self.assertIn("--require-hashes", line)
                self.assertNotRegex(line, r"\s-(?:U|-upgrade)\b")

    def test_notebook_omits_debug_environment_prints(self):
        notebook_source = "\n".join(self.code_cells)

        self.assertNotIn("sys.executable", notebook_source)
        self.assertNotIn("boto3.__version__", notebook_source)

    def test_no_b2_alias_or_native_api_literals(self):
        checked_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                ROOT / "01-video-frames-b2.ipynb",
                ROOT / "README.md",
                ROOT / ".env.example",
                ROOT / "b2_config.py",
            ]
        )

        for literal in [
            "b2" + "-native",
            "b2" + "_upload_file",
            "b2" + "_get_upload_url",
            "b2" + "_authorize_account",
            "B2_" + "KEY_ID",
        ]:
            self.assertNotIn(literal, checked_text)
        self.assertIsNone(re.search(r"\b" + "B2_" + "BUCKET" + r"\b", checked_text))


if __name__ == "__main__":
    unittest.main()
