import base64

from Crypto.Cipher import AES
from Crypto.Util import Counter


def decrypt_security_token(security_token: str) -> (str, str):
    """
    Decrypts security token into key and nonce pair

    security_token should match the securityToken value from the web response
    """

    # Do not change this
    master_key = "UIlTTEMmmLfGowo/UC60x2H45W6MdGgTRfo/umg4754="

    # Decode the base64 strings to ascii strings
    master_key = base64.b64decode(master_key)
    security_token = base64.b64decode(security_token)

    # Get the IV from the first 16 bytes of the securityToken
    iv = security_token[:16]
    encrypted_st = security_token[16:]

    # Initialize decryptor
    decryptor = AES.new(master_key, AES.MODE_CBC, iv)

    # Decrypt the security token
    decrypted_st = decryptor.decrypt(encrypted_st)

    # Get the audio stream decryption key and nonce from the decrypted security token
    key = decrypted_st[:16]
    nonce = decrypted_st[16:24]

    return key, nonce


def decrypt_file(path_file_encrypted: str, path_file_destination: str, key: str, nonce: str) -> None:
    """
    Decrypts an encrypted MQA file given the file, key and nonce
    """

    # Initialize counter and file decryptor
    counter = Counter.new(64, prefix=nonce, initial_value=0)
    decryptor = AES.new(key, AES.MODE_CTR, counter=counter)

    # Open and decrypt
    with open(path_file_encrypted, "rb") as f_src:
        audio_decrypted = decryptor.decrypt(f_src.read())

        # Replace with decrypted file
        with open(path_file_destination, "wb") as f_dst:
            f_dst.write(audio_decrypted)
