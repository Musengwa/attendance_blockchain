import json
from pathlib import Path
from solcx import compile_source, install_solc
from web3 import Web3

BASE = Path(__file__).parent
SOLC_VERSION = "0.8.19"
GANACHE_URL = "http://127.0.0.1:8545"


def main():
    # 1. Compile the Solidity source
    install_solc(SOLC_VERSION)
    source = (BASE / "contracts" / "Attendance.sol").read_text()
    compiled = compile_source(
        source, output_values=["abi", "bin"], solc_version=SOLC_VERSION
    )
    _, interface = compiled.popitem()

    # 2. Connect to Ganache
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    deployer = w3.eth.accounts[0]

    # 3. Deploy
    Contract = w3.eth.contract(abi=interface["abi"], bytecode=interface["bin"])
    tx_hash = Contract.constructor().transact({"from": deployer})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # 4. Save address + ABI for the rest of the project
    out = {"address": receipt.contractAddress, "abi": interface["abi"]}
    (BASE / "deployed.json").write_text(json.dumps(out, indent=2))

    print("Deployed at:", receipt.contractAddress)
    print("Deployed by:", deployer)


if __name__ == "__main__":
    main()