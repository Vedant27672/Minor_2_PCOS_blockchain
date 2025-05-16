# file to compare two different Proof of Work algorithms implemented in the Main source code for blockchain
# first algorithm generates nonce using random function
# second algorithm simply increments nonce by 1 after each iteration of generating valid hash value

from Blockchain import Blockchain
from Block import Block
from timeit import default_timer as timer
import random
import string
import threading

def random_char(length):
    """Generate a random string of given length."""
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

def add_transaction(block, transactions_length):
    """Add random transactions to the block."""
    for _ in range(transactions_length):
        if random.random() > 0.9:
            t = {
                "user": random_char(random.randint(0, 20)),
                "v_file": random_char(random.randint(0, 20)),
                "file_data": random_char(random.randint(0, 200)),
                "file_size": random.randint(0, 1000)
            }
            block.add_t(t)

def run_pow_comparison():
    pow_run = []
    pow2_run = []

    for difficulty in range(2, 6):
        block_index = random.randint(0, 2000)
        transactions_length = random.randint(10, 20)
        transactions = []

        # Create random block
        block = Block(block_index, transactions, "0")
        chain = Blockchain()
        Blockchain.difficulty = difficulty

        # Thread to add transactions on the fly
        tx_thread = threading.Thread(target=add_transaction, args=(block, transactions_length))
        tx_thread.start()

        # Proof of Work (random nonce)
        start = timer()
        print(chain.p_o_w(block))
        end = timer()
        print(end - start)
        pow_run.append(end - start)

        # Proof of Work 2 (iterative nonce)
        start = timer()
        print(chain.p_o_w_2(block))
        end = timer()
        print(end - start)
        pow2_run.append(end - start)

        tx_thread.join()

    print("------------Proof of Work with Random Nonce ------------")
    for idx, t in enumerate(pow_run, start=2):
        print(f"Difficulty {idx} Time : {round(t, 5)}")

    print("------------Proof of Work with Iterative Nonce ------------")
    for idx, t in enumerate(pow2_run, start=2):
        print(f"Difficulty {idx} Time : {round(t, 5)}")

    print("------------Proof of Work with Random Nonce ------------")
    for t in pow_run:
        print(round(t, 5))

    print("------------Proof of Work with Iterative Nonce ------------")
    for t in pow2_run:
        print(round(t, 5))

if __name__ == "__main__":
    run_pow_comparison()
