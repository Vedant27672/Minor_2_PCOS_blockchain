from hashlib import sha256

class Block:
    """
    Represents a single block in the blockchain.
    Each block contains an index, a list of transactions, the previous block's hash, and a nonce.
    """

    def __init__(self, index, transactions, prev_hash):
        self.index = index
        self.transactions = transactions  # List of transactions (file information)
        self.prev_hash = prev_hash        # Hash of the previous block
        self.nonce = 0                    # Nonce for Proof-of-Work

    def generate_hash(self):
        """
        Generates a SHA-256 hash of the block's contents.
        """
        block_contents = (
            str(self.index) +
            str(self.nonce) +
            self.prev_hash +
            str(self.transactions)
        )
        return sha256(block_contents.encode()).hexdigest()

    def add_transaction(self, transaction):
        """
        Adds a transaction to the block.
        """
        self.transactions.append(transaction)