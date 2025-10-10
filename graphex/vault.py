import base64
import secrets
import os
import typing
import random
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from OpenSSL import crypto

# DO NOT CHANGE these unless you know what you are doing
# This will break existing secrets
KDF_ALGORITHM = hashes.SHA256()
KDF_LENGTH = 32
KDF_ITERATIONS = 120000
SALT_SIZE = 16
CODEC = "utf-8"


def _encrypt(plaintext: str, password: str) -> bytes:
    """
    Produces an encrypted 'secret' when given a plaintext string to encrypt and a plaintext password to handle encryption/decryption.
    :param plaintext: the string to be encoded as a 'secret'
    :param password: the password to use to decrypt this 'secret' later

    :returns: an encrypted secret that is a combination of a random salt and the encrypted 'secret' (in bytes)
    """
    # Derive a symmetric key using the passsword and a fresh random salt.
    salt = secrets.token_bytes(SALT_SIZE)
    kdf = PBKDF2HMAC(
        algorithm=KDF_ALGORITHM, length=KDF_LENGTH, salt=salt,
        iterations=KDF_ITERATIONS)
    key = kdf.derive(password.encode(CODEC))

    # Encrypt the message.
    f = Fernet(base64.urlsafe_b64encode(key))
    ciphertext = f.encrypt(plaintext.encode(CODEC))

    return salt + ciphertext

def _decrypt(encrypted: bytes, password: str) -> str:
    """
    Decrypts a 'secret' that was previous encrypted using the 'encrypt' function from this same file.
    :param encrypted: an encrypted secret that is a combination of a random salt and the encrypted 'secret' (in bytes)
    :param password: the password that was used to encrypt the 'secret'

    :returns: the plaintext string that was originally encrypted
    """
    # Derive the symmetric key using the password and the salt from the encrypted bytes.
    kdf = PBKDF2HMAC(
        algorithm=KDF_ALGORITHM, length=KDF_LENGTH, salt=encrypted[:SALT_SIZE],
        iterations=KDF_ITERATIONS)
    key = kdf.derive(password.encode(CODEC))

    # Decrypt the message
    f = Fernet(base64.urlsafe_b64encode(key))
    plaintext = f.decrypt(encrypted[SALT_SIZE:])

    return plaintext.decode(CODEC)

def _encryptionToHexidecimalString(encrypted_secret: bytes) -> str:
    """
    Converts a 'secret' encrypted using the 'encrypt' function from this file into hexidecimal and then returns it as string.
    This is convient for plaintext storage of the encrypted bytes.
    :param encrypted_secret: an encrypted secret that is a combination of a random salt and the encrypted 'secret' (in bytes)

    :returns: a hexidecimal string
    """
    return encrypted_secret.hex()

def _hexStringToBytes(hexidecimal_string: str) -> bytes:
    """
    Converts a hexidecimal string into bytes.
    See 'encryptionToHexidecimalString' for the original conversion.
    :param hexidecimal_string: the hexidecimal string to convert back into bytes

    :returns: the hexidecimal string as bytes
    """
    return bytes.fromhex(hexidecimal_string)

def encryptString(plaintext: str, password: str) -> str:
    """
    Produces an encrypted 'secret' when given a plaintext string to encrypt and a plaintext password to handle encryption/decryption.
    :param plaintext: the string to be encoded as a 'secret'
    :param password: the password to use to decrypt this 'secret' later

    :returns: a hexidecimal string representation of the secret
    """
    return _encryptionToHexidecimalString(_encrypt(plaintext, password))

def decryptSecret(hexString: str, password: str) -> str:
    """
    Decrypts a 'secret' that was previous encrypted using the 'encryptString' function from this same file.
    :param hexString: a hexidecimal string representation of the secret
    :param password: the password that was used to encrypt the 'secret'

    :returns: the plaintext string that was originally encrypted
    """
    return _decrypt(_hexStringToBytes(hexString), password)

def generate_server_ssl_certs(directory_to_write_to: str):
    """
    Generates a new cert.pem and key.pem for the GraphEx server in the directory given.

    :param direcotry_to_write_to: the absolute path to a directory to write the new files to
    """
    # Define certificate details
    cert_file = "cert.pem"
    key_file = "key.pem"
    key_type = crypto.TYPE_RSA
    key_bits = 4096
    days_valid = 365
    subject = {
        "CN": "localhost",
        "O": "MITRE",
        "C": "US"
    }

    # Generate key pair
    key = crypto.PKey()
    key.generate_key(key_type, key_bits)

    # Create a self-signed certificate
    cert = crypto.X509()
    cert.get_subject().CN = subject["CN"]
    cert.get_subject().O = subject["O"]
    cert.get_subject().C = subject["C"]
    cert.set_serial_number(random.randint(1, 2**64 - 1))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(days_valid * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, "sha256")

    # Write the private key to a file
    with open(os.path.join(directory_to_write_to, key_file), "wb") as key_file_handle:
        key_file_handle.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

    # Write the certificate to a file
    with open(os.path.join(directory_to_write_to, cert_file), "wb") as cert_file_handle:
        cert_file_handle.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    print(f"Certificate and key have been generated and saved to {cert_file} and {key_file} respectively.")

def handle_ssl_context(ssl_certs_path: typing.Optional[str]) -> typing.Tuple[str, str]:
    """
    Determines which SSL certificates to use when serving the GraphEx server. Will use the provided path if it is a string.
    If the provided path is 'None', then this function will check if auto-generated certs already exist and will use those if they do exist.
    If auto-generated certs do not exist, then this function auto-generates new certificates to use.

    :param ssl_certs_path: The path to the SSL certificates to use for the GraphEx server OR 'None' to use or generate new certificates.
    :returns: a tuple of the absolute paths to the cert.pem and key.pem files (in that order)
    """
    if ssl_certs_path:
        return ( os.path.join(ssl_certs_path, "cert.pem"), os.path.join(ssl_certs_path, "key.pem") )

    print('No SSL certificates path provided to GraphEx... Checking for auto-generated certs in current directory...')

    autogenerated_dir = os.path.abspath( os.path.join('.', 'graphex_ssl_certificates') )

    key_name = 'key.pem'
    cert_name = 'cert.pem'
    found_key_name = False
    found_cert_name = False

    if os.path.exists(autogenerated_dir) and os.path.isdir(autogenerated_dir):
        for f_name in os.listdir(autogenerated_dir):
            if f_name == key_name:
                found_key_name = True
                continue
            if f_name == cert_name:
                found_cert_name = True

    if found_key_name and found_cert_name:
        print(f'Using previously generated SSL certificates found at path: {autogenerated_dir}')
        return ( os.path.join(autogenerated_dir, "cert.pem"), os.path.join(autogenerated_dir, "key.pem") )

    print(f'Failed to find auto-generated certs. Issuing new certificates and saving to directory: {autogenerated_dir}')

    # generate new certs
    try:
        os.mkdir(autogenerated_dir)
    except Exception:
        pass

    generate_server_ssl_certs(autogenerated_dir)
    return ( os.path.join(autogenerated_dir, "cert.pem"), os.path.join(autogenerated_dir, "key.pem") )
