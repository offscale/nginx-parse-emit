from functools import partial
from os import path, remove
from tempfile import mkstemp
from unittest import TestCase
from unittest import main as unittest_main

from crossplane import build, parse
from nginxparser_eb.nginxparser_eb import loads
from offutils import pp

from nginx_parse_emit.emit import api_proxy_block, server_block
from nginx_parse_emit.utils import OTemplate

configs_dir = partial(
    path.join, path.join(path.dirname(path.dirname(__file__)), "configs")
)


class TestParseEmit(TestCase):
    def setUp(self):
        # api_proxy_block
        self.location = "/api0"
        self.proxy_pass = "http://127.0.0.1:5000/awesome"
        self.parsed_api_block = loads(
            api_proxy_block(location=self.location, proxy_pass=self.proxy_pass)
        )

        # server_block_no_rest
        self.server_name = "offscale.io"
        self.listen = "443"
        self.parsed_server_block_no_rest = loads(
            server_block(server_name=self.server_name, listen=self.listen)
        )

        d = "/etc/letsencrypt/live/{server_name}".format(server_name=self.server_name)

        self.ssl_certificate = "{d}/fullchain.pem".format(d=d)
        self.ssl_certificate_key = "{d}/privkey.pem".format(d=d)

        self.nginx = configs_dir("nginx.conf")
        self.one_root = configs_dir("one_root.conf")
        self.two_roots = configs_dir("two_roots.conf")

    def test_one_root(self):
        pp(parse(self.nginx))
        # with open(self.one_root, "rt") as f0, open(self.two_roots, "rt") as f1, TemporaryFile('wt') as f2:
        #     pp(parse(f0.read()))

    def test_add_security(self):
        temp_file = mkstemp()[1]
        try:
            previous = ""
            with open(self.nginx, "rt") as f0, open(self.two_roots, "rt") as f1, open(
                temp_file, "wt"
            ) as f2:
                previous = OTemplate(f0.read()).substitute(SERVER_BLOCK=f1.read())
                f2.write(previous)
            pp(parse(temp_file))
            self.assertEqual(previous, build(parse(temp_file)))
        finally:
            remove(temp_file)
        # pp(tuple(lex(self.two_roots)))


if __name__ == "__main__":
    unittest_main()
