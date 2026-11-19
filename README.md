# Blockchain Attendance

A small, tamper-evident attendance log built on an Ethereum smart contract. Each attendance event (a member ID plus a timestamp) is written to the blockchain as an append-only record. Once a record is written it can't be edited or deleted, and only the authorised system account can add new ones.

The project has three parts:

- a **Solidity smart contract** that stores the records,
- a **Python wrapper** (`AttendanceChain`) that talks to the contract through `web3.py`,
- a **test suite** that runs against a throwaway in-memory blockchain, so no node is needed.

---

## Table of Contents

- [Why a Blockchain?](#why-a-blockchain)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running a Local Blockchain (Ganache)](#running-a-local-blockchain-ganache)
- [Usage](#usage)
  - [1. Check the connection](#1-check-the-connection)
  - [2. Deploy the contract](#2-deploy-the-contract)
  - [3. Run the demo](#3-run-the-demo)
  - [4. Use it from your own code](#4-use-it-from-your-own-code)
- [Smart Contract Reference](#smart-contract-reference)
- [Python API Reference](#python-api-reference)
- [Testing](#testing)
- [Security Model](#security-model)
- [Design Decisions & Limitations](#design-decisions--limitations)
- [Troubleshooting](#troubleshooting)
- [Possible Extensions](#possible-extensions)
- [License](#license)

---

## Why a Blockchain?

A normal database lets anyone with write access change or delete rows without leaving a trace. On a blockchain:

- **Records are immutable.** The contract has no update or delete function, so past entries can't be rewritten.
- **Every write is a signed transaction**, with a transaction hash you can audit.
- **Timestamps come from the block**, not from the client, so a caller can't backdate an entry.
- **Writes are restricted.** Only the account that deployed the contract can record attendance.

---

## How It Works

```
┌──────────────┐   mark_attendance("STU-001")   ┌────────────────────┐   transaction   ┌──────────────────────┐
│  Your app /  │ ─────────────────────────────▶ │  AttendanceChain   │ ──────────────▶ │  Attendance contract │
│   demo.py    │                                │  (web3.py wrapper) │                 │  (on Ganache / EVM)  │
│              │ ◀───────────────────────────── │                    │ ◀────────────── │                      │
└──────────────┘     list of record dicts       └────────────────────┘    call (read)  └──────────────────────┘
```

1. `deploy.py` compiles `contracts/attendance.sol` with `solc` 0.8.19 and deploys it to a local node (Ganache at `http://127.0.0.1:8545`) using the node's first account.
2. The contract's address and ABI are saved to `deployed.json`.
3. `AttendanceChain` loads `deployed.json`, connects to the node and exposes plain Python methods for writing and reading records.
4. Writes are transactions (they cost gas and are mined into a block). Reads are free `call`s.

---

## Project Structure

```
blockchain attendance/
├── contracts/
│   └── attendance.sol        # Solidity smart contract
├── tests/
│   └── test_blockchain.py    # pytest suite (in-memory chain, no node needed)
├── attendance_chain.py       # Python wrapper class around the contract
├── check-connection.py       # Sanity check: can we reach the node?
├── deploy.py                 # Compile + deploy the contract, write deployed.json
├── deployed.json             # Generated: contract address + ABI
├── demo.py                   # Example script: write two records, read them all
└── README.md
```

---

## Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ (developed on 3.13) | Runs the scripts and tests |
| [web3.py](https://web3py.readthedocs.io/) | 6.x / 7.x | Talks to the Ethereum node |
| [py-solc-x](https://solcx.readthedocs.io/) | latest | Downloads and runs the Solidity compiler |
| [eth-tester](https://github.com/ethereum/eth-tester) + py-evm | latest | In-memory chain used by the tests |
| pytest | latest | Test runner |
| [Ganache](https://archive.trufflesuite.com/ganache/) | any | Local Ethereum node for deploy/demo |
| Node.js | 16+ | Only needed if you use `ganache` from npm |

> The tests don't need Ganache. You only need it for `deploy.py`, `demo.py` and `check-connection.py`.

---

## Installation

```bash
# 1. Go to the project folder
cd "blockchain attendance"

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install Python dependencies
pip install "web3[tester]" py-solc-x pytest
```

`web3[tester]` pulls in `eth-tester` and `py-evm`, which the test suite needs.

The Solidity compiler (`solc` 0.8.19) installs itself automatically the first time you run `deploy.py` or the tests, through `install_solc()`. This needs internet access the first time.

---

## Running a Local Blockchain (Ganache)

You need a local Ethereum node listening on `http://127.0.0.1:8545`.

**Option A: Ganache CLI (npm)**

```bash
npm install -g ganache
ganache --port 8545
```

**Option B: Ganache desktop app**

Open Ganache, create a workspace, and set the RPC server port to **8545** (the desktop app defaults to 7545). Alternatively, change `GANACHE_URL` in `deploy.py`, `attendance_chain.py` and `check-connection.py`.

Ganache starts with 10 pre-funded, unlocked accounts. The project uses `accounts[0]` as the system or owner account.

> ⚠️ Ganache keeps state in memory by default. If you restart it, the deployed contract is gone and you'll need to run `deploy.py` again. To keep state between restarts, use `ganache --database.dbPath ./chaindata`.

---

## Usage

### 1. Check the connection

```bash
python check-connection.py
```

Expected output:

```
Connected: True
Accounts: 10
First account balance (ETH): 1000
```

### 2. Deploy the contract

```bash
python deploy.py
```

```
Deployed at: 0x888ed82F65d408f5feBFbe66C381454B157E9ea3
Deployed by: 0x...
```

This creates or overwrites `deployed.json` with the new contract address and ABI. Each run deploys a **new, empty** contract, so earlier records stay on the old contract address.

### 3. Run the demo

```bash
python demo.py
```

```
Records before: 0
Written, tx hash: 0x3f1c...
0 STU-001 2026-11-17 09:14:02
1 STU-002 2026-11-17 09:14:02
```

The demo writes two records (`STU-001` and `STU-002`), then reads back and prints every record stored in the contract. If you run it again, the records pile up, because the log is append-only.

### 4. Use it from your own code

```python
from attendance_chain import AttendanceChain

chain = AttendanceChain()                 # connects to Ganache, loads deployed.json

tx_hash = chain.mark_attendance("EMP-042")
print("Recorded in tx", tx_hash)

print("Total records:", chain.get_record_count())

for record in chain.get_records():
    print(f'{record["time"]}  {record["member_id"]}  (by {record["recorded_by"]})')
```

Connecting to a different node or contract file:

```python
chain = AttendanceChain(
    url="http://192.168.1.50:8545",
    deployed_file=Path("other_deployment.json"),
)
```

---

## Smart Contract Reference

**File:** `contracts/attendance.sol` · **Solidity:** `^0.8.19` · **License:** MIT

### Storage

```solidity
struct AttendanceRecord {
    address recordedBy;   // account that submitted the record
    string  memberID;     // e.g. "STU-001"
    uint256 timestamp;    // block.timestamp (Unix seconds)
}

address public owner;                 // deployer; only account allowed to write
AttendanceRecord[] private records;   // append-only list
```

### Functions

| Function | Type | Access | Description |
|----------|------|--------|-------------|
| `markAttendance(string memberID)` | transaction | `onlyOwner` | Appends a record with `msg.sender` and `block.timestamp`, then emits `AttendanceMarked`. |
| `getRecordCount() → uint256` | view | public | Number of stored records. |
| `getRecord(uint256 index) → (address, string, uint256)` | view | public | Returns `(recordedBy, memberID, timestamp)`. Reverts with `"Index out of range"` for an invalid index. |
| `owner() → address` | view | public | Address of the contract owner. |

### Events

```solidity
event AttendanceMarked(string memberID, uint256 timestamp);
```

Emitted on every successful write. Off-chain services can listen for this event to react to new check-ins in real time.

### Errors

| Revert message | Cause |
|----------------|-------|
| `Only the system can record attendance` | `markAttendance` was called by an account other than `owner`. |
| `Index out of range` | `getRecord` was called with `index >= getRecordCount()`. |

---

## Python API Reference

**File:** `attendance_chain.py`

### `AttendanceChain(url=GANACHE_URL, deployed_file=None, w3=None, info=None)`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `url` | `"http://127.0.0.1:8545"` | RPC endpoint of the node. Ignored if `w3` is given. |
| `deployed_file` | `./deployed.json` | Path to the JSON file holding `address` and `abi`. Ignored if `info` is given. |
| `w3` | `None` | An existing `Web3` instance, such as one using `EthereumTesterProvider` in tests. |
| `info` | `None` | A dict `{"address": ..., "abi": [...]}` to use instead of reading a file. |

Raises `ConnectionError` if the node can't be reached.

The write account is `w3.eth.accounts[0]`, which must be the same account that deployed the contract.

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `mark_attendance(member_id: str)` | `str` | Sends a transaction, waits for it to be mined and returns the transaction hash (hex). |
| `get_record_count()` | `int` | Number of records on chain. |
| `get_records()` | `list[dict]` | Every record, in insertion order. |

Each dict returned by `get_records()` looks like this:

```python
{
    "index": 0,
    "member_id": "STU-001",
    "timestamp": 1763370842,                 # Unix seconds (from the block)
    "time": "2026-11-17 09:14:02",           # local-time ISO string
    "recorded_by": "0xAbC...123",            # address that wrote the record
}
```

---

## Testing

The test suite compiles the contract and deploys a **fresh copy to an in-memory blockchain** (`EthereumTesterProvider`) for every test. No Ganache, no network access (after `solc` is downloaded once) and no shared state between tests.

```bash
pytest -v
```

| Test | What it checks |
|------|----------------|
| `test_starts_empty` | A new contract has zero records. |
| `test_mark_attendance_is_readable` | A written record can be read back with the correct ID and a timestamp. |
| `test_records_keep_their_order` | Records come back in the order they were written. |
| `test_same_member_can_be_recorded_twice` | The contract doesn't de-duplicate; it's a raw log. |
| `test_non_owner_cannot_write` | **Security:** a non-owner account is rejected and nothing is stored. |
| `test_out_of_range_read_fails` | Reading a non-existent index reverts. |

The tests accept both `ContractLogicError` (real nodes) and `TransactionFailed` (eth-tester), because the two backends report reverts differently.

---

## Security Model

- **Single writer.** Only `owner`, the deploying account, can call `markAttendance`. The `onlyOwner` modifier enforces this on-chain, so it can't be bypassed from the client side.
- **Public reads.** Anyone who can reach the node can read every record. The `private` keyword on `records` only hides it from the auto-generated getter. Data on a blockchain is never truly private, so **don't store personal data** such as names or emails. Store opaque IDs instead.
- **Trusted timestamps.** `block.timestamp` is set by the block producer. On Ganache that's your machine's clock. On public networks it can drift by a few seconds.
- **Key management.** Ganache accounts are unlocked and their keys are public. That's fine for local development but **not for production**. For a real network, sign transactions with a securely stored private key (for example from an environment variable or a hardware wallet) instead of `transact({"from": ...})`.

---

## Design Decisions & Limitations

- **Append-only by design.** There's no edit or delete. To correct a mistake you add a new record, and the history keeps both.
- **Duplicates are allowed.** De-duplication, rate limiting and "already checked in today" logic belong in the application layer.
- **No member registry.** The contract accepts any string as a member ID and doesn't check whether the member exists.
- **`get_records()` makes one call per record.** That's fine for hundreds of records but slow for many thousands. For large logs, read the `AttendanceMarked` events or add a paginated or batch getter to the contract.
- **Hard-coded node URL.** `GANACHE_URL` is defined separately in each script. Consider moving it to an environment variable or config file.
- **Ownership is fixed.** There's no `transferOwnership`. If the owner key is lost, the contract can't be written to again.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ConnectionError: Cannot reach blockchain node at http://127.0.0.1:8545` | Ganache isn't running, or it's on another port (the desktop app defaults to 7545). |
| `FileNotFoundError: ... deployed.json` | Run `python deploy.py` first. |
| `FileNotFoundError: ... contracts/Attendance.sol` (Linux/macOS) | The file on disk is `attendance.sol` (lowercase) but `deploy.py` and the tests load `Attendance.sol`. Windows ignores the case difference; Linux and macOS don't. Rename the file to `Attendance.sol`. |
| `Only the system can record attendance` | The sending account isn't the deployer. Make sure `accounts[0]` on the node is the account that ran `deploy.py`. Redeploy if you restarted Ganache with different accounts. |
| Calls fail or return nothing after restarting Ganache | Ganache state was wiped. Run `python deploy.py` again. |
| `solcx` can't download the compiler | You need internet access the first time. Behind a proxy, set `HTTPS_PROXY`, or install solc manually with `python -m solcx.install v0.8.19`. |
| `ModuleNotFoundError: eth_tester` | Install the tester extras: `pip install "web3[tester]"`. |

---

## Possible Extensions

- A **REST API** (Flask or FastAPI) or web dashboard on top of `AttendanceChain`.
- **QR code or RFID check-in** that calls `mark_attendance`.
- **Event listener** that subscribes to `AttendanceMarked` for live updates.
- **Multiple authorised recorders** through a role mapping (for example OpenZeppelin `AccessControl`).
- **Session or class IDs** added to each record, for example `markAttendance(memberID, sessionID)`.
- **Hashing member IDs** before storing them, to improve privacy.
- **Deployment to a public testnet** such as Sepolia, with proper private-key signing.
- A `requirements.txt` and a `.env` config for the node URL and keys.

---

## License

The smart contract is released under the **MIT License**, as declared by its SPDX header.
