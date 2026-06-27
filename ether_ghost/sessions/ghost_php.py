"""ShadowHalberd默认 PHP WebShell"""

import typing as t

from ..core.base import register_session, Option, OptionGroup, proxy_option
from ..core.php_session_common import (
    php_webshell_action_options,
    php_webshell_communication_options,
)
from .php_oneliner import PHPWebshellOneliner


@register_session
class GhostPHPWebshell(PHPWebshellOneliner):
    """ShadowHalberd默认 PHP WebShell

    使用一句话 PHP 的执行方式，默认：
    - 密码提交方式：POST
    - PHP 代码编码器：base64
    - 解码器：raw
    """

    session_type = "GHOST_PHP"
    readable_name = "XuLink PHP"
    conn_options: t.List[OptionGroup] = [
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
                    id="password_method",
                    name="Password Method",
                    type="select",
                    placeholder="POST",
                    default_value="POST",
                    alternatives=[
                        {"name": "POST", "value": "POST"},
                        {"name": "GET", "value": "GET"},
                    ],
                ),
                Option(
                    id="password",
                    name="Password",
                    type="text",
                    placeholder="******",
                    default_value=None,
                    alternatives=None,
                ),
                proxy_option(),
            ],
        },
        {
            "name": "Advanced Connection Config",
            "options": [
                Option(
                    id="timeout_refresh_client",
                    name="Refresh Session on Timeout",
                    type="checkbox",
                    placeholder="Reusing the same PHPSESSID may cause long-running requests to block subsequent ones",
                    default_value=True,
                    alternatives=None,
                ),
                Option(
                    id="https_verify",
                    name="Verify HTTPS Certificate",
                    type="checkbox",
                    placeholder=None,
                    default_value=True,
                    alternatives=None,
                ),
            ]
            + php_webshell_communication_options
            + php_webshell_action_options,
        },
    ]
