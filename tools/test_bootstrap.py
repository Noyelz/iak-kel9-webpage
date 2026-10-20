import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from dotenv import dotenv_values

spec=importlib.util.spec_from_file_location("bootstrap",Path(__file__).with_name("bootstrap.py"))
bootstrap=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def configure(self, root, config=None):
        return subprocess.run([sys.executable,"-c",bootstrap.ENV_CODE,str(root)],input=json.dumps(config or {}),text=True,capture_output=True,check=True)

    def test_generates_unique_secret_and_correct_env_quoting(self):
        with tempfile.TemporaryDirectory() as first,tempfile.TemporaryDirectory() as second:
            password="test-quote' and spaces # example"
            result=self.configure(Path(first),{"ANALYTICS_ENABLED":"1","ANALYTICS_DB_PASSWORD":password})
            self.configure(Path(second))
            one,two=dotenv_values(Path(first)/".env"),dotenv_values(Path(second)/".env")
            self.assertGreaterEqual(len(one["DJANGO_SECRET_KEY"]),64)
            self.assertNotEqual(one["DJANGO_SECRET_KEY"],two["DJANGO_SECRET_KEY"])
            self.assertEqual(one["ANALYTICS_DB_PASSWORD"],password)
            self.assertEqual(one["ANALYTICS_ENABLED"],"1")
            self.assertNotIn(password,result.stdout)
            self.assertNotIn(one["DJANGO_SECRET_KEY"],result.stdout)

    def test_preserves_existing_credentials_secret_and_comments(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            root.joinpath(".env").write_text("# keep comment\nDJANGO_SECRET_KEY='existing-secret'\nANALYTICS_DB_PASSWORD='existing-password'\nANALYTICS_DB_PORT='22333'\n",encoding="utf-8")
            self.configure(root,{"ANALYTICS_DB_PASSWORD":"new-password"})
            values=dotenv_values(root/".env")
            self.assertEqual(values["DJANGO_SECRET_KEY"],"existing-secret")
            self.assertEqual(values["ANALYTICS_DB_PASSWORD"],"existing-password")
            self.assertEqual(values["ANALYTICS_DB_PORT"],"22333")
            self.assertIn("# keep comment",root.joinpath(".env").read_text())

    def test_existing_placeholder_key_is_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            root.joinpath(".env").write_text("DJANGO_SECRET_KEY='replace-with-your-own-long-random-secret-key'\n",encoding="utf-8")
            self.configure(root)
            self.assertGreaterEqual(len(dotenv_values(root/".env")["DJANGO_SECRET_KEY"]),64)

    def test_launcher_finds_project_and_supported_python(self):
        root=bootstrap.project_root()
        self.assertTrue((root/"manage.py").is_file())
        self.assertTrue(bootstrap.valid_python(bootstrap.find_python(root)))


if __name__=="__main__":
    unittest.main()
