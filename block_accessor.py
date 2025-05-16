import json
import requests
import getpass
from config import Config

ADDR = "http://127.0.0.1:8800"

def user_login(username: str, password: str) -> bool:
    """Authenticate as regular user."""
    login_url = f"{ADDR}/login"
    response = requests.post(login_url, data={
        'username': username,
        'password': password
    })
    return response.status_code == 200

def get_block(block_index: int) -> dict | None:
    """Retrieve specific block by index."""
    chain_url = f"{ADDR}/chain"
    response = requests.get(chain_url)
    if response.status_code != 200:
        return None

    chain = response.json()
    for block in chain.get("chain", []):
        if block.get("index") == block_index:
            return block
    return None

def print_file_from_block(block_index: int, filename: str, username: str) -> None:
    """Print file contents from specific block."""
    password = getpass.getpass(f"Enter password for {username}: ")
    if not user_login(username, password):
        print("Authentication failed")
        return

    block = get_block(block_index)
    if not block:
        print(f"Block {block_index} not found")
        return

    for transaction in block.get("transactions", []):
        if (transaction.get("v_file") == filename and 
            transaction.get("owner") == username):
            print(f"\nFile: {filename}")
            print(f"Owner: {transaction.get('owner')}")
            print(f"Size: {transaction.get('file_size')} bytes")
            print("\nContents:")
            print(transaction.get("file_data"))
            return

    print(f"File {filename} not found in block {block_index} or you don't have access")

def main():
    import sys
    if len(sys.argv) != 4:
        print("Usage: python block_accessor.py <block_index> <filename> <username>")
        sys.exit(1)

    try:
        block_index = int(sys.argv[1])
    except ValueError:
        print("Block index must be an integer.")
        sys.exit(1)

    filename = sys.argv[2]
    username = sys.argv[3]
    print_file_from_block(block_index, filename, username)

if __name__ == "__main__":
    main()
