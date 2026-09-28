"""Live equality is an explicit integration test, never replaced by test doubles."""
import json
import os
from pathlib import Path
import pytest


@pytest.mark.mlx
def test_500_url_choice_gate_equivalence():
    path=os.environ.get('SEOJEV_EQUIVALENCE_REPORT')
    if not path:
        pytest.skip('Set SEOJEV_EQUIVALENCE_REPORT after a guarded live MLX evaluation on a safe host')
    result=json.loads(Path(path).read_text())
    assert result['status']=='completed', result.get('error')
    assert result['urls']==500
    eq=result['equivalence']
    assert eq['total']>0 and eq['matched']==eq['total'] and eq['mismatched']==0 and eq['passed']
