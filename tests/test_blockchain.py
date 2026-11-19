import sys
from pathlib import Path

import pytest
from solcx import compile_source, install_solc
from web3 import Web3, EthereumTesterProvider
from web3.exceptions import ContractLogicError
from eth_tester.exceptions import TransactionFailed

# EthereumTesterProvider surfaces reverts as TransactionFailed; real nodes use ContractLogicError
REVERT_ERRORS = (ContractLogicError, TransactionFailed)

BLOCKCHAIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BLOCKCHAIN_DIR))

from attendance_chain import AttendanceChain  # noqa: E402

SOLC_VERSION = "0.8.19"


@pytest.fixture
def chain():
    """A fresh contract on a throwaway in-memory chain for every test."""
    install_solc(SOLC_VERSION)
    source = (BLOCKCHAIN_DIR / "contracts" / "Attendance.sol").read_text()
    compiled = compile_source(
        source, output_values=["abi", "bin"], solc_version=SOLC_VERSION
    )
    _, interface = compiled.popitem()

    w3 = Web3(EthereumTesterProvider())
    Contract = w3.eth.contract(abi=interface["abi"], bytecode=interface["bin"])
    tx = Contract.constructor().transact({"from": w3.eth.accounts[0]})
    receipt = w3.eth.wait_for_transaction_receipt(tx)

    info = {"address": receipt.contractAddress, "abi": interface["abi"]}
    return AttendanceChain(w3=w3, info=info)


def test_starts_empty(chain):
    assert chain.get_record_count() == 0
    assert chain.get_records() == []


def test_mark_attendance_is_readable(chain):
    chain.mark_attendance("STU-001")
    records = chain.get_records()
    assert len(records) == 1
    assert records[0]["member_id"] == "STU-001"
    assert records[0]["timestamp"] > 0


def test_records_keep_their_order(chain):
    for member in ["STU-001", "STU-002", "STU-003"]:
        chain.mark_attendance(member)
    ids = [r["member_id"] for r in chain.get_records()]
    assert ids == ["STU-001", "STU-002", "STU-003"]


def test_same_member_can_be_recorded_twice(chain):
    # The chain is an append-only log; duplicate handling belongs in the app layer
    chain.mark_attendance("STU-001")
    chain.mark_attendance("STU-001")
    assert chain.get_record_count() == 2


def test_non_owner_cannot_write(chain):
    """Security check: an outside account must not be able to add records."""
    attacker = chain.w3.eth.accounts[1]
    with pytest.raises(REVERT_ERRORS):
        chain.contract.functions.markAttendance("FAKE-999").transact(
            {"from": attacker}
        )
    assert chain.get_record_count() == 0


def test_out_of_range_read_fails(chain):
    with pytest.raises(REVERT_ERRORS):
        chain.contract.functions.getRecord(5).call()