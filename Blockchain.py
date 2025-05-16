import random
from Block import Block

class Blockchain:
    DIFFICULTY = 3

    def __init__(self):
        self.pending = []
        self.chain = []
        genesis_block = Block(0, [], "0")
        genesis_block.hash = genesis_block.generate_hash()
        self.chain.append(genesis_block)

    def add_block(self, block, block_hash):
        if self.last_block().hash == block.prev_hash and self.is_valid(block, block_hash):
            block.hash = block_hash
            self.chain.append(block)
            return True
        return False

    def mine(self):
        if not self.pending:
            return False

        last_block = self.last_block()
        new_block = Block(last_block.index + 1, self.pending, last_block.hash)
        block_hash = self.proof_of_work(new_block)
        self.add_block(new_block, block_hash)
        self.pending = []
        return new_block.index

    def proof_of_work(self, block):
        block.nonce = 0
        block_hash = block.generate_hash()
        while not block_hash.startswith("0" * Blockchain.DIFFICULTY):
            block.nonce = random.randint(0, 99999999)
            block_hash = block.generate_hash()
        return block_hash

    def proof_of_work_incremental(self, block):
        block.nonce = 0
        block_hash = block.generate_hash()
        while not block_hash.startswith("0" * Blockchain.DIFFICULTY):
            block.nonce += 1
            block_hash = block.generate_hash()
        return block_hash

    def add_pending(self, transaction):
        self.pending.append(transaction)

    def check_chain_validity(self, chain):
        prev_hash = "0"
        for block in chain:
            if not (self.is_valid(block, block.hash) and prev_hash == block.prev_hash):
                return False
            prev_hash = block.hash
        return True

    @staticmethod
    def is_valid(block, block_hash):
        if not block_hash.startswith("0" * Blockchain.DIFFICULTY):
            return False
        return block.generate_hash() == block_hash

    def last_block(self):
        return self.chain[-1]
