import sys
import ssl
import socket
import re
import traceback
from cryptography import x509
from cryptography.hazmat.backends import default_backend

sys.path.append('../../')

from src.utils import convert_openssh_to_iana


def get_website_info(hostname):
    """
    Gathers all the required information to rate a web server.

    :param hostname: hostname of the webserver
    :return:
        cert -- used certificate to verify the server
        cipher_suite -- negotiated cipher suite
        protocol -- protocol name and version
        supported_versions -- SSL/TLS versions that the web server supports
    """
    if '/' in hostname:
        hostname = fix_hostname(hostname)
    supported_versions = test_ssl_versions(hostname)
    ssl_socket = create_session(hostname, 443)
    cipher_suite, protocol = get_cipher_suite_and_protocol(ssl_socket)
    cert = get_certificate(ssl_socket)
    ssl_socket.close()
    return cert, cipher_suite, protocol, supported_versions


def get_certificate(ssl_socket):
    """
    Gathers a certificate in a der format.

    :param ssl_socket: secured socket
    :return: gathered certificate
    """
    cert_pem = bytes(ssl_socket.getpeercert(binary_form=True))
    cert = x509.load_der_x509_certificate(cert_pem, default_backend())
    return cert


def get_cipher_suite_and_protocol(ssl_socket):
    """
    Gathers the cipher suite and the protocol from the ssl_socket.

    :param ssl_socket: secure socket
    :return: negotiated cipher suite and the protocol
    """
    cipher_suite = ssl_socket.cipher()[0]
    if '-' in cipher_suite:
        cipher_suite = convert_openssh_to_iana(cipher_suite)
    return cipher_suite, ssl_socket.version()


def test_ssl_versions(hostname):
    """
    Tests for all possible SSL/TLS versions which the server supports

    :param hostname: hostname of the website
    :return: secure socket with the highest version and the supported protocols
    """
    ssl_versions = [
        ssl.Options.OP_NO_TLSv1_3,
        ssl.Options.OP_NO_TLSv1_2,
        ssl.Options.OP_NO_TLSv1_1,
        ssl.Options.OP_NO_TLSv1,
        ssl.Options.OP_NO_SSLv3,
        ssl.Options.OP_NO_SSLv2
    ]
    supported_protocols = []
    for i in range(len(ssl_versions)):
        ssl_versions.pop()
        context = ssl.SSLContext()
        context.options -= ssl.Options.OP_NO_SSLv3
        for version in ssl_versions:
            context.options += version
        try:
            ssl_socket = create_session(hostname, 443, context)
            version = ssl_socket.version()
            ssl_socket.close()
            if version not in supported_protocols:
                supported_protocols.append(version)
        except ssl.SSLError:
            pass
    return supported_protocols


def create_session(hostname, port, context=ssl.create_default_context()):
    """
    Creates a secure connection to any server on any port with a defined context
    on a specific timeout.

    :param hostname: hostname of the website
    :param context: ssl context
    :param port: port
    :return: created secure socket
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 5 seconds
    sock.settimeout(5)
    ssl_socket = context.wrap_socket(sock, server_hostname=hostname)
    try:
        ssl_socket.connect((hostname, port))
    except socket.timeout:
        print("Server nepodpruje HTTPS protokol alebo server neodpovedá na požiadavky.")
        exit(1)
    except socket.gaierror:
        print("Nastala chyba v DNS službe.")
        exit(socket.EAI_FAIL)
    return ssl_socket


def fix_hostname(hostname):
    """
    Extracts the domain name.

    :param hostname: hostname address to be checked
    :return: fixed hostname address
    """
    print('Upravujem webovú adresu...')
    if hostname[:4] == 'http':
        # Removes http(s):// and anything after TLD (*.com)
        hostname = re.search('[/]{2}([^/]+)', hostname).group(1)
    else:
        # Removes anything after TLD (*.com)
        hostname = re.search('^([^/]+)', hostname).group(0)
    print('Použítá webová adresa: {}'.format(hostname))
    return hostname
