from __future__ import absolute_import, print_function

from functools import partial
from os import path
from unittest import TestCase, main as unittest_main

from nginxparser import loads
from offutils import pp

from nginx_parse_emit.emit import api_proxy_block, server_block, upsert_ssl_cert_to_443_block

configs_dir = partial(path.join,
                      path.join(path.dirname(path.dirname(__file__)), 'configs'))


class TestParseEmit(TestCase):
    def setUp(self):
        # api_proxy_block
        self.location = '/api0'
        self.proxy_pass = 'http://127.0.0.1:5000/awesome'
        self.parsed_api_block = loads(api_proxy_block(location=self.location, proxy_pass=self.proxy_pass))

        # server_block_no_rest
        self.server_name = 'offscale.io'
        self.listen = '443'
        self.parsed_server_block_no_rest = loads(server_block(server_name=self.server_name, listen=self.listen))

        d = '/etc/letsencrypt/live/{server_name}'.format(server_name=self.server_name)

        self.ssl_certificate = '{d}/fullchain.pem'.format(d=d)
        self.ssl_certificate_key = '{d}/privkey.pem'.format(d=d)

        self.nginx = configs_dir('nginx.conf')
        self.two_roots = configs_dir('two_roots.conf')

    def test_add_security(self):
        output0 = upsert_ssl_cert_to_443_block(self.two_roots, self.ssl_certificate, self.ssl_certificate_key)
        output1 = upsert_ssl_cert_to_443_block(output0, self.ssl_certificate, self.ssl_certificate_key)
        output1 = upsert_ssl_cert_to_443_block(output1, self.ssl_certificate, self.ssl_certificate_key)
        self.assertItemsEqual(output0, output1)
        pp(output1)
        # print(dumps(output1))


if __name__ == '__main__':
    unittest_main()
