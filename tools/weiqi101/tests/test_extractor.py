"""Tests for 101weiqi HTML → qqdata extraction."""

from tools.weiqi101.extractor import extract_qqdata, is_rate_limited_page


def test_extract_simple_qqdata():
    """Extract qqdata from minimal HTML."""
    html = '''
    <html>
    <script>
    var qqdata = {"publicid": 78000, "boardsize": 19, "firsthand": 1};
    </script>
    </html>
    '''
    result = extract_qqdata(html)
    assert result is not None
    assert result["publicid"] == 78000
    assert result["boardsize"] == 19


def test_extract_with_nested_braces():
    """Extract qqdata with nested objects."""
    html = '''
    <script>
    var qqdata = {"id": 1, "andata": {"0": {"pt": "pd", "o": 1, "subs": [1]}}};
    </script>
    '''
    result = extract_qqdata(html)
    assert result is not None
    assert result["andata"]["0"]["pt"] == "pd"


def test_extract_missing_qqdata():
    """Return None when qqdata not found."""
    html = "<html><body>No puzzle here</body></html>"
    result = extract_qqdata(html)
    assert result is None


def test_extract_with_escaped_strings():
    """Handle escaped characters in JSON strings."""
    html = r'''
    <script>
    var qqdata = {"id": 1, "name": "puzzle \"test\""};
    </script>
    '''
    result = extract_qqdata(html)
    assert result is not None
    assert result["id"] == 1


def test_extract_malformed_json():
    """Return None for invalid JSON after qqdata."""
    html = '''
    <script>
    var qqdata = {invalid json here};
    </script>
    '''
    result = extract_qqdata(html)
    assert result is None


def test_is_rate_limited_captcha_page():
    """Detect CAPTCHA/rate-limited page (no qqdata + Tencent CAPTCHA script)."""
    html = '''
    <html><head>
    <title> 101围棋网</title>
    <script src="https://turing.captcha.qcloud.com/TCaptcha.js"></script>
    </head><body>Please verify</body></html>
    '''
    assert is_rate_limited_page(html) is True


def test_is_rate_limited_normal_puzzle_page():
    """Normal puzzle page with qqdata is NOT rate-limited."""
    html = '''
    <html>
    <script src="https://turing.captcha.qcloud.com/TCaptcha.js"></script>
    <script>var qqdata = {"id": 1};</script>
    </html>
    '''
    assert is_rate_limited_page(html) is False


def test_is_rate_limited_plain_page():
    """Plain page without qqdata and without captcha is NOT rate-limited."""
    html = "<html><body>Some other page</body></html>"
    assert is_rate_limited_page(html) is False
