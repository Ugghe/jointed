import os

_AUTH = {"Authorization": f"Bearer {os.environ.get('JOINTED_ADMIN_TOKEN', 'test-admin-token')}"}

_CSV = """word,tag
bass,Fish
bass,Instrument
newword999,TestTagCsv
"""


def test_csv_upload_merge(client) -> None:
    files = {"file": ("words.csv", _CSV, "text/csv")}
    r = client.post("/v1/import/words-csv", files=files, headers=_AUTH)
    assert r.status_code == 200, r.text
    data = r.json()
    touched = data["links_added"] + data["links_already_present"]
    assert touched >= 3
    assert data["rows_read"] == 3


def test_csv_bad_header_400(client) -> None:
    bad = "a,b,c\n1,2,3\n"
    files = {"file": ("bad.csv", bad, "text/csv")}
    r = client.post("/v1/import/words-csv", files=files, headers=_AUTH)
    assert r.status_code == 400
