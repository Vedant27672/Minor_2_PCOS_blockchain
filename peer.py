import json
from flask import Flask, request
from Blockchain import Blockchain
from Block import Block

app = Flask(__name__)
blockchain = Blockchain()
peers = []

@app.route("/new_transaction", methods=["POST"])
def new_transaction():
    """
    Add a new transaction to the list of pending transactions.
    """
    file_data = request.get_json()
    required_fields = ["user", "v_file", "file_data", "file_size"]
    if not all(field in file_data and file_data[field] for field in required_fields):
        return "Transaction does not have valid fields!", 404
    blockchain.add_pending(file_data)
    return "Success", 201

@app.route("/chain", methods=["GET"])
def get_chain():
    """
    Return the full blockchain.
    """
    chain = [block.__dict__ for block in blockchain.chain]
    print(f"Chain Len: {len(chain)}")
    return json.dumps({"length": len(chain), "chain": chain})

@app.route("/mine", methods=["GET"])
def mine_unconfirmed_transactions():
    """
    Mine pending transactions.
    """
    result = blockchain.mine()
    if result:
        return f"Block #{result} mined successfully."
    return "No pending transactions to mine."

@app.route("/pending_tx", methods=["GET"])
def get_pending_tx():
    """
    Return the list of pending transactions.
    """
    return json.dumps(blockchain.pending)

@app.route("/add_block", methods=["POST"])
def validate_and_add_block():
    """
    Add a block mined by another node to the chain.
    """
    block_data = request.get_json()
    try:
        block = Block(
            block_data["index"],
            block_data["transactions"],
            block_data["prev_hash"]
        )
        hashl = block_data["hash"]
    except KeyError:
        return "Invalid block data.", 400

    added = blockchain.add_block(block, hashl)
    if not added:
        return "The Block was discarded by the node.", 400
    return "The block was added to the chain.", 201

if __name__ == "__main__":
    app.run(port=8800, debug=True)
