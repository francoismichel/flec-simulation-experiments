import os
import http.server

# Don't use the nobody user but the current user to run CGI scripts
from functools import partial


def fixed_nobody():
    return http.server.nobody


http.server.nobody = os.getuid()
http.server.nobody_uid = fixed_nobody

# Taken from http/server.py
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--cgi', action='store_true',
                        help='Run as CGI Server')
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Specify alternative directory '
                             '[default:current directory]')
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    if args.cgi:
        handler_class = http.server.CGIHTTPRequestHandler
    else:
        handler_class = partial(http.server.SimpleHTTPRequestHandler,
                                directory=args.directory)
    http.server.test(HandlerClass=handler_class, port=args.port, bind=args.bind)
