from eth.vm.forks.byzantium.computation import (
    ByzantiumComputation,
)
from eth.exceptions import (
    Halt,
    VMError
)
from vdb.vdb import VyperDebugCmd
from vyper.exceptions import ParserException


class DebugVMError(VMError, ParserException):
    lineno = None
    col_offset = None

    def __init__(self, message, item=None, source_code=None):
        self.message = message
        if item is not None:
            self.lineno, self.col_offset = item
        if source_code is not None:
            self.source_code = source_code.splitlines()


class DebugComputation(ByzantiumComputation):
    enable_debug = False
    source_code = None
    source_map = None
    stdin = None
    stdout = None
    step_mode = False
    trace = False
    pc = 0

    @classmethod
    def run_debugger(self, computation, line_no):
        res = VyperDebugCmd(
            computation,
            line_no=line_no,
            source_code=self.source_code,
            source_map=self.source_map,
            stdin=self.stdin,
            stdout=self.stdout
        )
        res.cmdloop()
        self.step_mode = res.step_mode
        return line_no

    @classmethod
    def get_pos(cls, pc):
        pc_pos_map = cls.source_map['line_number_map']['pc_pos_map']
        if pc in pc_pos_map:
            return pc_pos_map[pc]

    @classmethod
    def get_line_no(cls, pc):
        pos = cls.get_pos(pc)
        if pos:
            return pos[0]
        return None

    @classmethod
    def is_breakpoint(cls, pc, continue_line_nos):
        line_no = cls.get_line_no(pc)
        # PC breakpoint.
        if pc in cls.source_map['line_number_map'].get('pc_breakpoints', {}):
            return True, line_no
        # Line no breakpoint.
        breakpoint_lines = set(cls.source_map['line_number_map']['breakpoints'])
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
                if cls.trace:
                    print(
                        "NEXT OPCODE: 0x%x (%s) | pc: %s..%s" %
                        (opcode,
                        opcode_fn.mnemonic,
                        cls.pc,
                        pc_to_execute)
                    )
                cls.pc = pc_to_execute

                is_breakpoint, line_no = cls.is_breakpoint(pc_to_execute, continue_line_nos)

                if (is_breakpoint or cls.step_mode) and cls.enable_debug:
                    cls.run_debugger(computation, line_no)
                    continue_line_nos.append(line_no)

                try:
                    opcode_fn(computation=computation)
                except VMError as e:  # re-raise with more details.
                    pos = cls.get_pos(pc_to_execute)
                    msg = e.args[0]
                    msg = "" if len(msg) == 0 else msg

                    raise DebugVMError(
                        message=msg,
                        item=pos,
                        source_code=cls.source_code
                    ) from e
                except Halt:
                    break

        return computation
