from sys import modules, _getframe

from nginx_parse_emit.utils import DollarTemplate, ensure_semicolon

_default_comment = 'Emitted by {}'.format(modules[__name__].__name__)


def api_proxy_block(location, proxy_pass):
    return DollarTemplate('''location /$nginx_route {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass $api_route;
        proxy_redirect off;
    }''').safe_substitute(nginx_route=location[1:] if location.startswith('/') else location,
                          api_route=proxy_pass)


def server_block(server_name, listen, comment=None, rest=None):
    return DollarTemplate('''server {
         # $comment
         server_name $server_name;
         listen $listen;$rest\n}''').safe_substitute(server_name=server_name, listen=listen,
                                                     comment=comment or '{}.{}'.format(_default_comment,
                                                                                       _getframe().f_code.co_name),
                                                     rest='' if rest is None
                                                     else ''.join('{line}\n'.format(line=ensure_semicolon(line))
                                                                  for line in rest.splitlines()))
