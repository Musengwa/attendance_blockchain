from web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

print("Connected:", w3.is_connected())
print("Accounts:", len(w3.eth.accounts))
print("First account balance (ETH):", w3.from_wei(w3.eth.get_balance(w3.eth.accounts[0]), "ether"))