"""SQL entry points retain offline reuse while providing first-use installation."""
import duckdb
import pytest

from ev_pipeline.acquire import ROOT
from ev_pipeline import pipeline


@pytest.mark.parametrize("entry_point", ["pipeline", "standalone"])
def test_standalone_schema_and_queries_reuse_installed_spatial_offline(entry_point):
    # An unavailable repository makes an accidental re-download fail. The
    # pipeline has already loaded the installed, version-specific local binary.
    connection = (pipeline.connect(":memory:", offline=True) if entry_point == "pipeline"
                  else duckdb.connect(":memory:", config={"extension_directory": str(pipeline.EXT)}))
    with connection as con:
        con.execute("SET custom_extension_repository='http://127.0.0.1:1'")
        con.execute((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
        assert con.execute("""SELECT count(*) FROM information_schema.tables
                              WHERE table_type='BASE TABLE'""").fetchone()[0] == 23
        assert con.execute("SELECT ST_AsText(ST_Point(151,-33))").fetchone()[0] == "POINT (151 -33)"
        con.execute((ROOT / "sql/analysis_queries.sql").read_text(encoding="utf-8"))


def test_offline_pipeline_rejects_an_empty_extension_cache(tmp_path, monkeypatch):
    extensions = tmp_path / "never_installed"
    monkeypatch.setattr(pipeline, "EXT", extensions)
    with pytest.raises(RuntimeError, match="Run python -m ev_pipeline all online once"):
        pipeline.connect(":memory:", offline=True)
    assert list(extensions.rglob("*")) == []
