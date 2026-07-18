from pathlib import Path
import pandas as pd
from c3e.reports import parse_sections
from c3e.audit import add_context_features, add_frontal_feature, add_mentions, load_yaml

def test_sections():
    text = """CLINICAL HISTORY: evaluate for edema
FINDINGS: mild edema.
IMPRESSION: pulmonary edema."""
    s = parse_sections(text)
    assert s["history"] == "evaluate for edema"
    assert "mild edema" in s["findings"]

def test_features(tmp_path: Path):
    cfg = load_yaml(Path(__file__).parents[1] / "configs" / "mimic.yaml")
    terms = load_yaml(Path(__file__).parents[1] / "configs" / "terms.yaml")
    df = pd.DataFrame({
        "subject_id": [1, 2],
        "study_id": [10, 20],
        "context": ["Evaluate for pulmonary edema", ""],
        "ViewPosition": ["AP", "PA"],
        "Cardiomegaly": [0, 1],
        "Edema": [1, 0],
        "Pleural Effusion": [0, 0],
        "Atelectasis": [0, 0],
        "Consolidation": [0, 0],
    })
    df = add_context_features(df, cfg)
    df = add_frontal_feature(df, cfg)
    df = add_mentions(df, cfg, terms)
    assert df.loc[0, "Edema__mention_any"]
    assert df.loc[1, "context_state"] == "absent"
