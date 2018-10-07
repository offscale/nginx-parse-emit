from __future__ import absolute_import

from unittest import TestCase, main as unittest_main

from nginxparser import loads, dumps

from nginx_parse_emit.emit import api_proxy_block, server_block, secure_attr, redirect_block
from nginx_parse_emit.utils import merge_into, upsert_by_location, apply_attributes


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

        self.two_roots = loads('''
        server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 80;
    }
        
        server {
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
} 
        ''')

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
        self.assertEqual('''server {
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
}''', dumps(parsed))
        self.assertEqual([[['server'],
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
                              ['proxy_pass', 'http://127.0.0.1:5000/awesome'], ['proxy_redirect', 'off']]]]]],
                         parsed)

    def test_upsert_by_location(self):
        # upsert_by_name('/api0', self.parsed_server_block_no_rest, self.parsed_api_block)

        self.assertEqual('''server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 80;
}
server {
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
}''', dumps(upsert_by_location('/api0', self.two_roots, self.parsed_api_block)))

        self.assertEqual('''server {
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
}''', dumps(upsert_by_location('/api0',
                               merge_into(self.parsed_server_block_no_rest, self.parsed_api_block),
                               self.parsed_api_block)))
        self.assertEqual('''server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 443;
 
    location /api0 {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass WRONG_DOMAIN;
        proxy_redirect off;
    }
}''', dumps(upsert_by_location('/api0',
                               merge_into(self.parsed_server_block_no_rest, self.parsed_api_block),
                               loads(
                                   api_proxy_block(location=self.location,
                                                   proxy_pass='WRONG_DOMAIN')))))

    def test_attributes_simple(self):
        aa = apply_attributes(self.parsed_server_block_no_rest,
                              secure_attr(self.ssl_certificate, self.ssl_certificate_key))
        self.assertEqual([[['server'],
                           [['# Emitted by nginx_parse_emit.emit.server_block',
                             '\n'],
                            ['server_name', self.server_name],
                            ['listen', self.listen],
                            ['ssl', 'on'],
                            ['ssl_certificate', self.ssl_certificate],
                            ['ssl_certificate_key', self.ssl_certificate_key],
                            ['fastcgi_param', 'HTTPS               on'],
                            ['fastcgi_param', 'HTTP_SCHEME         https']]]],
                         aa)
        self.assertEqual(dumps(aa), '''server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 443;
    ssl on;
    ssl_certificate /etc/letsencrypt/live/offscale.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/offscale.io/privkey.pem;
    fastcgi_param HTTPS               on;
    fastcgi_param HTTP_SCHEME         https;
}''')

    def test_attributes_two_roots(self):
        expect_config_s = '''server { 
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 80;
    return 301 https://$server_name$request_uri;
 }

 server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 443;
    ssl on;
    ssl_certificate /etc/letsencrypt/live/offscale.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/offscale.io/privkey.pem;
    fastcgi_param HTTPS               on;
    fastcgi_param HTTP_SCHEME         https;

    location /api0 {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:5000/awesome;
        proxy_redirect off;
    }

}'''

        aa = apply_attributes(self.two_roots, secure_attr(self.ssl_certificate, self.ssl_certificate_key), append=False)
        self.assertEqual([[['server'],
                           [['# Emitted by nginx_parse_emit.emit.server_block', '\n'],
                            ['server_name', self.server_name],
                            ['listen', '80']]],
                          [['server'],
                           [['listen', self.listen],
                            ['ssl', 'on'],
                            ['ssl_certificate', self.ssl_certificate],
                            ['ssl_certificate_key', self.ssl_certificate_key],
                            ['fastcgi_param', 'HTTPS               on'],
                            ['fastcgi_param', 'HTTP_SCHEME         https'],
                            [['location', '/api0'],
                             [['proxy_set_header', 'Host $http_host'],
                              ['proxy_set_header', 'X-Real-IP $remote_addr'],
                              ['proxy_set_header', 'X-Scheme $scheme'],
                              ['proxy_set_header', 'X-Forwarded-Proto $scheme'],
                              ['proxy_set_header',
                               'X-Forwarded-For $proxy_add_x_forwarded_for'],
                              ['proxy_pass', self.proxy_pass],
                              ['proxy_redirect', 'off']]]]]],
                         aa)

        self.assertEqual('''server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name offscale.io;
    listen 80;
}
server {
    listen 443;
    ssl on;
    ssl_certificate /etc/letsencrypt/live/offscale.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/offscale.io/privkey.pem;
    fastcgi_param HTTPS               on;
    fastcgi_param HTTP_SCHEME         https;
 
    location /api0 {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:5000/awesome;
        proxy_redirect off;
    }
}''', dumps(aa))

    def test_merge_roots(self):
        server_name = 'foo'
        self.assertEqual('''server {
    server_name foo;
    listen 80;
    return 301 https://$server_name$request_uri;
}
server {
    # Emitted by nginx_parse_emit.emit.server_block
    server_name foo;
    listen 443;
}''', dumps(loads(redirect_block(server_name=server_name, port=80)) +
            loads(server_block(server_name=server_name, listen=443))))


if __name__ == '__main__':
    unittest_main()
