from evm.vm.forks.byzantium import ByzantiumVM
from evm.vm.forks.byzantium.state import ByzantiumState

from vdb.debug_computation import DebugComputation

from eth_tester.backends.pyevm.main import (
    get_default_genesis_params,
    generate_genesis_state,
    get_default_genesis_params,
    get_default_account_keys,
    PyEVMBackend
)


class DebugState(ByzantiumState):
    computation_class = DebugComputation


class DebugVM(ByzantiumVM):
    _state_class = DebugState  # type: Type[BaseState]


def _setup_tester_chain():
    from evm.chains.tester import MainnetTesterChain
    from evm.db import get_db_backend

    class DebugNoProofVM(DebugVM):
        """Byzantium VM rules, without validating any miner proof of work"""

        def validate_seal(self, header):
            pass

    class MainnetTesterNoProofChain(MainnetTesterChain):
        vm_configuration = ((0, DebugNoProofVM), )

    genesis_params = get_default_genesis_params()
    account_keys = get_default_account_keys()
    genesis_state = generate_genesis_state(account_keys)

    base_db = get_db_backend()

    chain = MainnetTesterNoProofChain.from_genesis(base_db, genesis_params, genesis_state)
    return account_keys, chain


class PyEVMDebugBackend(PyEVMBackend):

    def __init__(self, ):
        super().__init__()

    def reset_to_genesis(self):
        self.account_keys, self.chain = _setup_tester_chain()


def set_debug_info(source_code, source_map, stdin=None, stdout=None):
    setattr(DebugComputation, 'source_code', source_code)
    setattr(DebugComputation, 'source_map', source_map)
    setattr(DebugComputation, 'stdin', stdin)
    setattr(DebugComputation, 'stdout', stdout)
