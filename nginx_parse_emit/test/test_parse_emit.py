from __future__ import absolute_import

from unittest import TestCase, main as unittest_main

from nginxparser import loads, dumps

from nginx_parse_emit.emit import api_proxy_block, server_block
from nginx_parse_emit.utils import merge_into


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

    def test_api_proxy_block(self):
        self.assertEqual(
            self.parsed_api_block,
            [[['location', self.location], [['proxy_set_header', 'Host $http_host'],
                                            ['proxy_set_header', 'X-Real-IP $remote_addr'],
                                            ['proxy_set_header', 'X-Scheme $scheme'],
                                            ['proxy_set_header', 'X-Forwarded-Proto $scheme'],
                                            ['proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'],
                                            ['proxy_pass', self.proxy_pass],
                                            ['proxy_redirect', 'off']]]]
        )

    def test_server_block_no_rest(self):
        self.assertEqual(
            self.parsed_server_block_no_rest,
            [[['server'], [['# Emitted by nginx_parse_emit.emit.server_block', '\n'], ['server_name', self.server_name],
                           ['listen', self.listen]]]]
        )

    def test_server_block_rest(self):
        server_name = 'offscale.io'
        listen = '443'
        comment = None
        rest = '''
         goodbye
         cruel
         world
        '''
        self.assertEqual(
            loads(server_block(server_name=server_name, listen=listen, comment=comment, rest=rest)),
            [[['server'], [['# Emitted by nginx_parse_emit.emit.server_block', '\n'], ['server_name', server_name],
                           ['listen', listen],
                           ['goodbye'],
                           ['cruel'],
                           ['world']]]]
        )

    def test_server_proxy_merge(self):
        parsed = merge_into(self.parsed_server_block_no_rest, self.parsed_api_block, self.parsed_api_block)
        self.assertEqual(dumps(parsed),
                         '''server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 443;
 
    location /api0 {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:5000/awesome;
        proxy_redirect off;
    }
 
    location /api0 {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:5000/awesome;
        proxy_redirect off;
    }
}''')
        self.assertEqual(parsed,
                         [[['server'],
                           [['# Emitted by nginx_parse_emit.emit.server_block', '\n'], ['server_name', 'offscale.io'],
                            ['listen', '443'], [['location', '/api0'], [['proxy_set_header', 'Host $http_host'],
                                                                        ['proxy_set_header', 'X-Real-IP $remote_addr'],
                                                                        ['proxy_set_header', 'X-Scheme $scheme'],
                                                                        ['proxy_set_header',
                                                                         'X-Forwarded-Proto $scheme'],
                                                                        ['proxy_set_header',
                                                                         'X-Forwarded-For $proxy_add_x_forwarded_for'],
                                                                        ['proxy_pass', 'http://127.0.0.1:5000/awesome'],
                                                                        ['proxy_redirect', 'off']]],
                            [['location', '/api0'],
                             [['proxy_set_header', 'Host $http_host'], ['proxy_set_header', 'X-Real-IP $remote_addr'],
                              ['proxy_set_header', 'X-Scheme $scheme'],
                              ['proxy_set_header', 'X-Forwarded-Proto $scheme'],
                              ['proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'],
                              ['proxy_pass', 'http://127.0.0.1:5000/awesome'], ['proxy_redirect', 'off']]]]]])


if __name__ == '__main__':
    unittest_main()
