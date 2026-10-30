from micro_http.router import match_path, Router

def test_basic_match():
    matched, params = match_path("/users/<id>", "/users/123")
    assert matched is True
    assert params == {"id": "123"}

def test_slug_with_hyphen():
    matched, params = match_path("/articles/<slug>", "/articles/hello-world-2026")
    assert matched is True
    assert params == {"slug": "hello-world-2026"}
