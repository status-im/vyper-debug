from evm.vm.forks.byzantium.computation import (
    ByzantiumComputation,
)
from evm.exceptions import (
    Halt,
)
from vdb.vdb import VyperDebugCmd


class DebugComputation(ByzantiumComputation):
    source_code = None
    source_map = None

    def run_debugger(self, computation, line_no):
        VyperDebugCmd(
            computation,
            line_no=line_no,
            source_code=self.source_code,
            source_map=self.source_map,
            stdin=None,
            stdout=None
        ).cmdloop()

    @classmethod
    def apply_computation(cls, state, message, transaction_context):

        with cls(state, message, transaction_context) as computation:

            print('hello!!!!!!')
            import ipdb; ipdb.set_trace()

            # Early exit on pre-compiles
            if message.code_address in computation.precompiles:
                computation.precompiles[message.code_address](computation)
                return computation

            for opcode in computation.code:
                opcode_fn = computation.get_opcode_fn(opcode)

                pc_to_execute = max(0, computation.code.pc - 1)
                computation.logger.trace(
                    "OPCODE: 0x%x (%s) | pc: %s",
                    opcode,
                    opcode_fn.mnemonic,
                    pc_to_execute,
                )

                # if pc_to_execute in self.debugger.breakpoints:
                #     import ipdb; ipdb.set_trace()

                try:
                    opcode_fn(computation=computation)
                except Halt:
                    break

        return computation
