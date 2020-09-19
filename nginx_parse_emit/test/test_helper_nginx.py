from functools import partial
from os import path
from platform import python_version_tuple
from unittest import TestCase, main as unittest_main

from nginx_parse_emit.utils import merge_into

if python_version_tuple()[0] == "2":
    xrange = range

from nginxparser import loads, dumps

from nginx_parse_emit.emit import (
    api_proxy_block,
    server_block,
    upsert_ssl_cert_to_443_block,
    upsert_redirect_to_443_block,
)

configs_dir = partial(
    path.join, path.join(path.dirname(path.dirname(__file__)), "configs")
)


class TestParseEmit(TestCase):
    def setUp(self):
        # api_proxy_block
        self.location = "/api0"
        self.proxy_pass = "http://127.0.0.1:5020/awesome"
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
        self.two_roots = configs_dir("two_roots.conf")
        self.one_root = configs_dir("one_root.conf")

        with open(self.one_root, "rt") as f:
            self.one_root_content = f.read()

        with open(self.two_roots, "rt") as f:
            self.two_roots_content = f.read()

    def test_add_ssl_cert(self):
        output0 = upsert_ssl_cert_to_443_block(
            self.two_roots,
            self.server_name,
            self.ssl_certificate,
            self.ssl_certificate_key,
        )
        output1 = upsert_ssl_cert_to_443_block(
            output0, self.server_name, self.ssl_certificate, self.ssl_certificate_key
        )
        for _ in range(5):
            output1 = upsert_ssl_cert_to_443_block(
                output1,
                self.server_name,
                self.ssl_certificate,
                self.ssl_certificate_key,
            )

        output1_s = dumps(output1)

        self.assertItemsEqual(output0, output1)
        self.assertNotEqual(self.two_roots_content, output1_s)
        for term in self.ssl_certificate, self.ssl_certificate_key:
            self.assertIn(term, output1_s)

    def test_add_redirect(self):
        output0 = upsert_redirect_to_443_block(self.one_root, self.server_name)
        output1 = upsert_redirect_to_443_block(output0, self.server_name)
        for _ in range(5):
            output1 = upsert_redirect_to_443_block(output1, self.server_name)

        output1_s = dumps(output1)

        self.assertItemsEqual(output0, output1)
        self.assertNotEqual(self.one_root_content, dumps(output0))
        for term in self.server_name, "443":
            self.assertIn(term, output1_s)

    def test_add_redirect_and_cert(self):
        output0 = upsert_ssl_cert_to_443_block(
            upsert_redirect_to_443_block(self.one_root, self.server_name),
            self.server_name,
            self.ssl_certificate,
            self.ssl_certificate_key,
        )
        output1 = upsert_ssl_cert_to_443_block(
            upsert_redirect_to_443_block(output0, self.server_name),
            self.server_name,
            self.ssl_certificate,
            self.ssl_certificate_key,
        )
        for _ in range(5):
            output1 = upsert_ssl_cert_to_443_block(
                upsert_redirect_to_443_block(output1, self.server_name),
                self.server_name,
                self.ssl_certificate,
                self.ssl_certificate_key,
            )

        output1_s = dumps(output1)

        for term in (
            self.server_name,
            "443",
            self.ssl_certificate,
            self.ssl_certificate_key,
        ):
            self.assertIn(term, output1_s)

    def test_proxy_add(self):
        output0 = upsert_ssl_cert_to_443_block(
            upsert_redirect_to_443_block(self.one_root, self.server_name),
            self.server_name,
            self.ssl_certificate,
            self.ssl_certificate_key,
        )
        output1 = merge_into(self.server_name, output0, self.parsed_api_block)
        for i in range(5):
            self.parsed_api_block[0][1][5][1] += str(i)
            output1 = merge_into(self.server_name, output1, self.parsed_api_block)

        output1_s = dumps(output1)
        self.assertEqual(output1_s.count(self.location), 1)
        for term in (
            self.proxy_pass,
            self.server_name,
            "443",
            self.ssl_certificate,
            self.ssl_certificate_key,
            "proxy_pass http://127.0.0.1:5020/awesome01234;",
        ):
            self.assertIn(term, output1_s)


if __name__ == "__main__":
    unittest_main()
