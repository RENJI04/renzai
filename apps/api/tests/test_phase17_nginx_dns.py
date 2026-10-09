"""Release regression for Docker service address changes behind Nginx."""

import re
from pathlib import Path


def test_nginx_re_resolves_compose_services() -> None:
    config = (Path(__file__).resolve().parents[3] / "infrastructure/nginx/renzai.conf").read_text(
        encoding="utf-8"
    )

    assert "resolver 127.0.0.11 valid=1s ipv6=off;" in config
    assert "set $renzai_api_upstream renzai-api;" in config
    assert "set $renzai_web_upstream renzai-web;" in config
    proxy_targets = re.findall(r"^\s*proxy_pass\s+([^;]+);", config, flags=re.MULTILINE)
    assert proxy_targets == [
        "http://$renzai_api_upstream:8000",
        "http://$renzai_api_upstream:8000",
        "http://$renzai_api_upstream:8000",
        "http://$renzai_api_upstream:8000",
        "http://$renzai_web_upstream:3000",
    ]
