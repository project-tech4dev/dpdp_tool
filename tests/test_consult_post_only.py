"""The consult form sends personal data: POST body only, never the URL or the console."""

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent / "dpdp_tool"


def test_submit_consult_request_is_post_only():
    tree = ast.parse((ROOT / "api.py").read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "submit_consult_request")
    methods = next(ast.literal_eval(kw.value) for d in fn.decorator_list if isinstance(d, ast.Call)
                   for kw in d.keywords if kw.arg == "methods")
    assert methods == ["POST"]


def test_consult_form_posts_body_and_logs_no_data():
    js = (ROOT / "public" / "js" / "dpdp-index.js").read_text()
    body = js[js.index("async function submitConsult"):js.index("async function loadConsultSectors")]
    assert "submit_consult_request?" not in body          # nothing appended to the URL
    assert re.search(r"method:\s*'POST'", body) and "body:cp" in body
    for args in re.findall(r"console\.\w+\((.*?)\);", body):
        assert "'[dpdp] consult" in args and "cj" not in args.split("?")[-1] and "e)" not in args, args
