import pytest

from vyper import compiler

from eth_tester import (
    EthereumTester,
)
from web3.providers.eth_tester import (
    EthereumTesterProvider,
)
from web3 import (
    Web3,
)
from vdb.vdb import (
    set_evm_opcode_debugger,
    set_evm_opcode_pass,
    VyperDebugCmd
)
from vdb.source_map import (
    produce_source_map
)


@pytest.fixture(scope="module")
def tester():
    t = EthereumTester()
    return t


def zero_gas_price_strategy(web3, transaction_params=None):
    return 0  # zero gas price makes testing simpler.


@pytest.fixture(scope="module")
def w3(tester):
    w3 = Web3(EthereumTesterProvider(tester))
    w3.eth.setGasPriceStrategy(zero_gas_price_strategy)
    return w3


def _get_contract(w3, source_code, *args, **kwargs):
    abi = compiler.mk_full_signature(source_code)
    bytecode = '0x' + compiler.compile(source_code).hex()
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    stdin = kwargs['stdin'] if 'stdin' in kwargs else None
    stdout = kwargs['stdout'] if 'stdout' in kwargs else None

    source_map = produce_source_map(source_code)
    set_evm_opcode_debugger(source_code=source_code, source_map=source_map, stdin=stdin, stdout=stdout)

    value = kwargs.pop('value', 0)
    value_in_eth = kwargs.pop('value_in_eth', 0)
    value = value_in_eth * 10**18 if value_in_eth else value  # Handle deploying with an eth value.
    gasPrice = kwargs.pop('gasPrice', 0)
    deploy_transaction = {
        'from': w3.eth.accounts[0],
        'data': contract._encode_constructor_data(args, kwargs),
        'value': value,
        'gasPrice': gasPrice
    }
    tx = w3.eth.sendTransaction(deploy_transaction)
    address = w3.eth.getTransactionReceipt(tx)['contractAddress']
    contract = w3.eth.contract(address, abi=abi, bytecode=bytecode)
    # Filter logs.
    contract._logfilter = w3.eth.filter({
        'fromBlock': w3.eth.blockNumber - 1,
        'address': contract.address
    })
    return contract


@pytest.fixture
def get_contract(w3):
    def get_contract(source_code, *args, **kwargs):
        return _get_contract(w3, source_code, *args, **kwargs)
    return get_contract

@pytest.fixture
def get_last_out():
    def _get_last_out(stdout):
        return stdout.getvalue().splitlines()[-2].split(VyperDebugCmd.prompt)[1]
    return _get_last_out
