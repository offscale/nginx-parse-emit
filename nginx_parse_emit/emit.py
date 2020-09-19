from collections import namedtuple
from sys import modules, _getframe

from nginxparser import loads

from nginx_parse_emit.utils import (
    DollarTemplate,
    ensure_semicolon,
    _prevent_slash,
    ensure_nginxparser_instance,
)

_default_comment = "Emitted by {}".format(modules[__name__].__name__)


def api_proxy_block(location, proxy_pass):  # type: (str, str) -> str
    return DollarTemplate(
        """location /$location {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass       $proxy_pass;
        proxy_redirect   off;
    }"""
    ).safe_substitute(location=_prevent_slash(location), proxy_pass=proxy_pass)


def server_block(
    server_name, listen, comment=None, rest=None
):  # type: (str, str, str or None, str or None) -> str
    return DollarTemplate(
        """server {
         # $comment
         server_name $server_name;
         listen $listen;$rest\n}"""
    ).safe_substitute(
        server_name=server_name,
        listen=listen,
        comment=comment or "{}.{}".format(_default_comment, _getframe().f_code.co_name),
        rest=""
        if rest is None
        else "".join(
            "{line}\n".format(line=ensure_semicolon(line)) for line in rest.splitlines()
        ),
    )


def autoindex_block(location, root):  # type: (str, str) -> str
    return DollarTemplate(
        """location /$location {
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
               return     204;
            }
            root                 $root;
            autoindex            on;
            autoindex_exact_size off;
            autoindex_format     json;
            autoindex_localtime  on;
        """
    ).safe_substitute(location=_prevent_slash(location), root=root)


def proxy_1_1_block(location, proxy_pass):  # type: (str, str) -> str
    return DollarTemplate(
        """location /$location {
            proxy_pass         $proxy_pass;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade $http_upgrade;
            proxy_set_header   Connection "upgrade";
        }"""
    ).safe_substitute(location=_prevent_slash(location), proxy_pass=proxy_pass)


def html5_block(location, root):  # type: (str, str) -> str
    return DollarTemplate(
        """location /$location {
            try_files  $uri$args $uri$args/ /index.html;
            root       $root;
            index      index.html index.htm;
            add_header 'Cache-Control' 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0';
            expires    off;
        }"""
    ).safe_substitute(location=_prevent_slash(location), root=root)


def redirect_block(
    server_name, port, redirect_to=None
):  # type: (str, str, str or None) -> str
    return DollarTemplate(
        """server {
      server_name $server_name;
      listen      $port;
      return      301 $redirect_to;
    }"""
    ).safe_substitute(
        server_name=server_name,
        port=port,
        redirect_to=redirect_to or "https://$server_name$request_uri",
    )


def secure_attr(
    ssl_certificate, ssl_certificate_key, port=None
):  # type: (str, str, str or None) -> str
    return DollarTemplate(
        """listen $port;
    ssl                 on;
    ssl_certificate     $ssl_certificate;
    ssl_certificate_key $ssl_certificate_key;
    fastcgi_param       HTTPS               on;
    fastcgi_param       HTTP_SCHEME         https;"""
    ).safe_substitute(
        port=port or 443,
        ssl_certificate=ssl_certificate,
        ssl_certificate_key=ssl_certificate_key,
    )


def upsert_redirect_to_443_block(conf_file, server_name):  # type: (str, str) -> []
    conf = ensure_nginxparser_instance(conf_file)

    server_name_idx = None
    found = False

    ListenStmIdx = namedtuple("ListenStmIdx", ("return_stm", "i", "j", "k"))
    listen_stm_idx = ListenStmIdx(False, None, None, None)
    for i, tier in enumerate(conf):
        for j, statement in enumerate(tier):
            for k, stm in enumerate(statement):
                if statement[k][0] == "server_name" and statement[k][1] == server_name:
                    server_name_idx = i
                elif statement[k][0] == "listen":
                    if not listen_stm_idx.return_stm:
                        listen_stm_idx = ListenStmIdx(return_stm=False, i=i, j=j, k=k)
                    if str(statement[k][1]).startswith("443"):
                        found = True
                    else:
                        statement[k][1] = "443"
                elif statement[k][0] == "return":
                    listen_stm_idx = ListenStmIdx(
                        return_stm=True,
                        i=listen_stm_idx.i,
                        j=listen_stm_idx.j,
                        k=listen_stm_idx.k,
                    )
    if listen_stm_idx.return_stm:
        conf[listen_stm_idx.i][listen_stm_idx.j][listen_stm_idx.k][1] = "80"
    elif not found and server_name_idx is not None:
        conf.insert(
            server_name_idx,
            loads(redirect_block(server_name=server_name, port="80"))[0],
        )
    return conf


def upsert_ssl_cert_to_443_block(
    conf_file, server_name, ssl_certificate, ssl_certificate_key
):  # type: (str, str, str, str) -> []
    conf = ensure_nginxparser_instance(conf_file)

    for i, tier in enumerate(conf):
        listen_or_server_name_idx = -1
        for j, statement in enumerate(tier):
            if ["listen", "443"] in statement or ["listen", "443 ssl"] in statement:
                update = False
                correct_server_name = False
                last_ssl_certificate = None
                last_ssl_certificate_key = None

                for k, stm in enumerate(statement):
                    if (
                        statement[k][0] == "server_name"
                        and statement[k][1] == server_name
                    ):
                        correct_server_name = True
                    elif conf[i][j][k][0] == "ssl_certificate":
                        last_ssl_certificate = i, j, k
                        update = True
                    elif conf[i][j][k][0] == "ssl_certificate_key":
                        last_ssl_certificate_key = i, j, k
                        update = True
                    elif conf[i][j][k][0] == "listen":
                        listen_or_server_name_idx = k
                        conf[i][j][k][1] = "443 ssl"
                    elif conf[i][j][k][0] == "server_name":
                        listen_or_server_name_idx = k

                if correct_server_name:
                    if update:
                        conf[last_ssl_certificate[0]][last_ssl_certificate[1]][
                            last_ssl_certificate[2]
                        ][1] = ssl_certificate
                        conf[last_ssl_certificate_key[0]][last_ssl_certificate_key[1]][
                            last_ssl_certificate_key[2]
                        ][1] = ssl_certificate_key
                    elif not update and "ssl_certificate" not in conf[i][j]:
                        conf[i][j].insert(
                            listen_or_server_name_idx + 1,
                            ["ssl_certificate", ssl_certificate],
                        )
                        conf[i][j].insert(
                            listen_or_server_name_idx + 2,
                            ["ssl_certificate_key", ssl_certificate_key],
                        )

    return conf
