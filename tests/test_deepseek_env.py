"""Temporary files and fictional credentials only; never read the real .env."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.validation import InputError
from harness.deepseek_trial import load_project_env, main


class ProjectEnvTests(unittest.TestCase):
    def test_literal_pairs_quotes_equals_and_existing_environment_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("\ufeff# synthetic_fixture\nDEEPSEEK_API_KEY='fictional-key'\n"
                            'DEEPSEEK_MODEL_ID="fixture-model"\nEMPTY=from-file\n'
                            'LITERAL=$(do-not-execute) ${HOME}=suffix # literal\n'
                            'DUP=first\nDUP=second\n', encoding="utf-8")
            env = {"DEEPSEEK_API_KEY": "fictional-existing", "EMPTY": ""}
            load_project_env(path, env)
            self.assertEqual(env["DEEPSEEK_API_KEY"], "fictional-existing")
            self.assertEqual(env["EMPTY"], "")
            self.assertEqual(env["DEEPSEEK_MODEL_ID"], "fixture-model")
            self.assertEqual(env["LITERAL"], "$(do-not-execute) ${HOME}=suffix # literal")
            self.assertEqual(env["DUP"], "first")

    def test_absolute_project_path_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
            (Path(root) / ".env").write_text("DEEPSEEK_API_KEY=fictional-root-key", encoding="utf-8")
            (Path(other) / ".env").write_text("DEEPSEEK_API_KEY=fictional-wrong-key", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(other)
                env = {}
                with patch("harness.deepseek_trial.PROJECT_ROOT", Path(root).resolve()):
                    load_project_env(environ=env)
                self.assertEqual(env["DEEPSEEK_API_KEY"], "fictional-root-key")
            finally:
                os.chdir(previous)

    def test_missing_file_is_optional_and_invalid_file_is_atomic_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            env = {"EXISTING": "keep"}
            load_project_env(path, env)
            for invalid in ("export SECRET=fictional-secret", "fictional-secret", "KEY='fictional-secret", "KEY=bad\x00value"):
                path.write_text("VALID=not-applied\n" + invalid, encoding="utf-8")
                with self.assertRaises(InputError) as caught:
                    load_project_env(path, env)
                self.assertNotIn("fictional-secret", str(caught.exception))
                self.assertEqual(env, {"EXISTING": "keep"})

    def test_cli_loads_before_model_default_without_network_or_real_env(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text(
                "DEEPSEEK_API_KEY=fictional-key\nDEEPSEEK_MODEL_ID=fixture-model\n", encoding="utf-8")
            seen = []
            def reject(settings):
                seen.append((settings.model_id, os.environ["DEEPSEEK_API_KEY"]))
                raise InputError("synthetic configuration rejection")
            with patch("harness.deepseek_trial.PROJECT_ROOT", Path(directory)), patch.dict(os.environ, {}, clear=True), \
                    patch("harness.deepseek_trial.create_adapter", side_effect=reject), \
                    patch("harness.deepseek_trial.save"), patch("sys.argv", ["trial", "--connection-only"]), \
                    patch("sys.stderr") as stderr:
                with self.assertRaises(SystemExit) as caught:
                    main()
                self.assertEqual(caught.exception.code, 2)
                self.assertEqual(seen, [("fixture-model", "fictional-key")])
                self.assertNotIn("fictional-key", str(stderr.write.call_args_list))
