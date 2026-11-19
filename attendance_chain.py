import json
from datetime import datetime
from pathlib import Path
from web3 import Web3

BASE = Path(__file__).parent
GANACHE_URL = "http://127.0.0.1:8545"


class AttendanceChain:
    
     def __init__(self, url=GANACHE_URL, deployed_file=None, w3=None, info=None):
        self.w3 = w3 or Web3(Web3.HTTPProvider(url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot reach blockchain node at {url}")

        if info is None:
            info = json.loads((deployed_file or BASE / "deployed.json").read_text())
        self.contract = self.w3.eth.contract(
            address=info["address"], abi=info["abi"]
        )
        # Account that deployed the contract = the only one allowed to write
        self.sender = self.w3.eth.accounts[0]

     def mark_attendance(self, member_id: str) -> str:
        """Write one attendance event. Returns the transaction hash."""
        tx_hash = self.contract.functions.markAttendance(member_id).transact(
            {"from": self.sender}
        )
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash.hex()

     def get_record_count(self) -> int:
        return self.contract.functions.getRecordCount().call()

     def get_records(self) -> list[dict]:
        """Read every attendance record back from the chain."""
        records = []
        for i in range(self.get_record_count()):
            recorded_by, member_id, timestamp = (
                self.contract.functions.getRecord(i).call()
            )
            records.append({
                "index": i,
                "member_id": member_id,
                "timestamp": timestamp,
                "time": datetime.fromtimestamp(timestamp).isoformat(sep=" "),
                "recorded_by": recorded_by,
            })
        return records