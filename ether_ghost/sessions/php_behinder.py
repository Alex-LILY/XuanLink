import typing as t

from ..core.base import (
    register_session,
    Option,
    OptionGroup,
    proxy_option,
)
from .wsm_behinder import BehinderSessionBase


def _common_options() -> t.List[OptionGroup]:
    return [
        {
            "name": "Basic Connection Config",
            "options": [
                Option(
                    id="url",
                    name="URL",
                    type="text",
                    placeholder="http://xxx.com/shell.php",
                    default_value=None,
                    alternatives=None,
                ),
                Option(
                    id="password",
                    name="Password",
                    type="text",
                    placeholder="rebeyond",
                    default_value="rebeyond",
                    alternatives=None,
                ),
                proxy_option(),
            ],
        },
        {
            "name": "Advanced Connection Config",
            "options": [
                Option(
                    id="https_verify",
                    name="Verify HTTPS Certificate",
                    type="checkbox",
                    placeholder=None,
                    default_value=False,
                    alternatives=None,
                ),
            ],
        },
    ]


@register_session
class PHPWebshellBehinderAES(BehinderSessionBase):
    session_type = "BEHINDER_PHP_AES"
    readable_name = "Behinder AES"
    script = "php"
    mode = 0
    conn_options = _common_options()


@register_session
class PHPWebshellBehinderXor(BehinderSessionBase):
    session_type = "BEHINDER_PHP_XOR"
    readable_name = "Behinder XOR"
    script = "php"
    mode = 1
    conn_options = _common_options()
