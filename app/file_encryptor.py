from app import aes
import sys
import os

def read_file(file_path):
    """Read binary data from a file."""
    with open(file_path, 'rb') as f:
        return f.read()

def write_file(file_path, data):
    """Write binary data to a file."""
    with open(file_path, 'wb') as f:
        f.write(data)

def encrypt_file(input_file, output_file, password):
    """Encrypt the contents of input_file and write to output_file."""
    data = read_file(input_file)
    ciphertext = aes.encrypt(password.encode('utf-8'), data)
    write_file(output_file, ciphertext)

def decrypt_file(input_file, output_file, password):
    """Decrypt the contents of input_file and write to output_file."""
    data = read_file(input_file)
    plaintext = aes.decrypt(password.encode('utf-8'), data)
    write_file(output_file, plaintext)

def print_usage():
    print("Usage: python file_encryptor.py [encrypt|decrypt] <input_file> <output_file> <password>")

def main():
    if len(sys.argv) != 5:
        print_usage()
        sys.exit(1)

    mode, infile, outfile, password = sys.argv[1:5]

    if mode == 'encrypt':
        encrypt_file(infile, outfile, password)
    elif mode == 'decrypt':
        decrypt_file(infile, outfile, password)
    else:
        print("Invalid mode. Use 'encrypt' or 'decrypt'.")
        print_usage()
        sys.exit(1)

if __name__ == '__main__':
    main()
