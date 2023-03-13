import os
from pathlib import Path

import pytest


from ewoc_work_plan.cli import main

__author__ = "Mickael Savinaud"
__copyright__ = "Mickael Savinaud"
__license__ = "MIT"



def test_main(capsys):
    """CLI Tests"""
    # capsys is a pytest fixture that allows asserts agains stdout/stderr
    # https://docs.pytest.org/en/stable/capture.html
    main(['21HTC', '2018-01-01', '2018-03-01', '/tmp/test_21HTC-t.json', str(Path(os.getenv('HOME')) / '.config/eodag/eodag.yml'), 'creodias', 'false'])
    
    assert Path('/tmp/test_21HTC-t.json').exists()
