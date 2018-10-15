from evm.vm.forks.byzantium.computation import (
    ByzantiumComputation,
)
from evm.exceptions import (
    Halt,
)
from vdb.vdb import VyperDebugCmd


class DebugComputation(ByzantiumComputation):
    enable_debug = False
    source_code = None
    source_map = None
    stdin = None
    stdout = None

    @classmethod
    def run_debugger(self, computation, line_no):
        VyperDebugCmd(
            computation,
            line_no=line_no,
            source_code=self.source_code,
            source_map=self.source_map,
            stdin=self.stdin,
            stdout=self.stdout
        ).cmdloop()
        return line_no

    @classmethod
    def get_line_no(cls, pc):
        pc_pos_map = cls.source_map['line_number_map']['pc_pos_map']
        if pc in pc_pos_map:
            return pc_pos_map[pc][0]

    @classmethod
    def is_breakpoint(cls, pc, continue_line_nos):
        breakpoint_lines = cls.source_map['line_number_map']['breakpoints']
        line_no = cls.get_line_no(pc)
        if line_no is not None:
            if line_no in continue_line_nos:  # already been here, skip.
                return False, line_no
            return line_no in breakpoint_lines, line_no
        return False, None

    @classmethod
    def apply_computation(cls, state, message, transaction_context):

        with cls(state, message, transaction_context) as computation:

            # Early exit on pre-compiles
            if message.code_address in computation.precompiles:
                computation.precompiles[message.code_address](computation)
                return computation

            continue_line_nos = []
            for opcode in computation.code:
                opcode_fn = computation.get_opcode_fn(opcode)

                pc_to_execute = max(0, computation.code.pc - 1)
                computation.logger.trace(
                    "OPCODE: 0x%x (%s) | pc: %s",
                    opcode,
                    opcode_fn.mnemonic,
                    pc_to_execute,
                )

                is_breakpoint, line_no = cls.is_breakpoint(pc_to_execute, continue_line_nos)

                if is_breakpoint and cls.enable_debug:
                    cls.run_debugger(computation, line_no)
                    continue_line_nos.append(line_no)

                try:
                    opcode_fn(computation=computation)
                except Halt:
                    break

        return computation
