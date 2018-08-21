from sys import modules, _getframe

from nginx_parse_emit.utils import DollarTemplate, ensure_semicolon, _prevent_slash

_default_comment = 'Emitted by {}'.format(modules[__name__].__name__)


def api_proxy_block(location, proxy_pass):  # type: (str, str) -> str
    return DollarTemplate('''location /$location {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass $proxy_pass;
        proxy_redirect off;
    }''').safe_substitute(location=_prevent_slash(location),
                          proxy_pass=proxy_pass)


def server_block(server_name, listen, comment=None, rest=None):  # type: (str, str, str or None, str or None) -> str
    return DollarTemplate('''server {
         # $comment
         server_name $server_name;
         listen $listen;$rest\n}''').safe_substitute(server_name=server_name, listen=listen,
                                                     comment=comment or '{}.{}'.format(_default_comment,
                                                                                       _getframe().f_code.co_name),
                                                     rest='' if rest is None
                                                     else ''.join('{line}\n'.format(line=ensure_semicolon(line))
                                                                  for line in rest.splitlines()))


def autoindex_block(location, root):  # type: (str, str) -> str
    return DollarTemplate('''location /$location {
          if ($request_method = 'OPTIONS') {
               add_header 'Access-Control-Allow-Origin' 'http://localhost:4400';
               add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
               #
               # Custom headers and headers various browsers *should* be OK with but aren't
               #
               add_header 'Access-Control-Allow-Headers' 'DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Content-Range,Range';
               #
               # Tell client that this pre-flight info is valid for 20 days
               #
               add_header 'Access-Control-Max-Age' 1728000;
               add_header 'Content-Type' 'text/plain; charset=utf-8';
               add_header 'Content-Length' 0;
               return 204;
            }
            root $root;
            autoindex on;
            autoindex_exact_size off;
            autoindex_format json;
            autoindex_localtime on;
        ''').safe_substitute(location=_prevent_slash(location), root=root)


def proxy_1_1_block(location, proxy_pass):  # type: (str, str) -> str
    return DollarTemplate('''location /$location {
            proxy_pass $proxy_pass;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }''').safe_substitute(location=_prevent_slash(location), proxy_pass=proxy_pass)


def html5_block(location, root):  # type: (str, str) -> str
    return DollarTemplate('''location /$location {
            try_files $uri$args $uri$args/ /index.html;
            root   $root;
            index  index.html index.htm;
            add_header 'Cache-Control' 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0';
            expires off;
        }''').safe_substitute(location=_prevent_slash(location), root=root)
