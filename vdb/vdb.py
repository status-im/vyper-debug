import cmd
import readline

from eth_utils import to_hex

import evm
from evm import constants
from evm.vm.opcode import as_opcode

from vyper.opcodes import opcodes as vyper_opcodes
from vdb.variables import (
    parse_global,
    parse_local
)

commands = [
    'continue',
    'locals',
    'globals'
]


def history(stdout):
    for i in range(1, readline.get_current_history_length() + 1):
        stdout.write("%3d %s" % (i, readline.get_history_item(i)) + '\n')


logo = """
__     __
\ \ _ / /
 \ v v /  Vyper Debugger
  \   /  0.0.0b1
   \ /  "help" to get a list of commands
    v
"""


class VyperDebugCmd(cmd.Cmd):
    prompt = '\033[92mvdb\033[0m> '
    intro = logo

    def __init__(self, computation, line_no=None, source_code=None, source_map=None,
                 stdout=None, stdin=None):
        if source_map is None:
            source_map = {}
        self.computation = computation
        self.source_code = source_code
        self.line_no = line_no
        self.global_vars = source_map.get("globals", {})
        self.local_vars = source_map.get("locals", {})
        super().__init__(stdin=stdin, stdout=stdout)
        if stdout or stdin:
            self.use_rawinput = False

    def _print_code_position(self):

        if not all((self.source_code, self.line_no)):
            self.stdout.write('No source loaded' + '\n')
            return

        lines = self.source_code.splitlines()
        begin = self.line_no - 1 if self.line_no > 1 else 0
        end = self.line_no + 1 if self.line_no < len(lines) else self.line_no
        for idx, line in enumerate(lines[begin - 1:end]):
            line_number = begin + idx
            if line_number == self.line_no:
                self.stdout.write("--> \033[92m{}\033[0m\t{}".format(line_number, line) + '\n')
            else:
                self.stdout.write("    \033[92m{}\033[0m\t{}".format(line_number, line) + '\n')

    def preloop(self):
        super().preloop()
        self._print_code_position()

    def postloop(self):
        self.stdout.write('Exiting vdb' + '\n')
        super().postloop()

    def do_state(self, *args):
        """ Show current EVM state information. """
        self.stdout.write('Block Number => {}'.format(self.computation.state.block_number) + '\n')
        self.stdout.write('Program Counter => {}'.format(self.computation.code.pc) + '\n')
        self.stdout.write('Memory Size => {}'.format(len(self.computation._memory)) + '\n')
        self.stdout.write('Gas Remaining => {}'.format(self.computation.get_gas_remaining()) + '\n')

    def do_globals(self, *args):
        if not self.global_vars:
            self.stdout.write('No globals found.' + '\n')
        self.stdout.write('Name\t\tType' + '\n')
        for name, info in self.global_vars.items():
            self.stdout.write('self.{}\t\t{}'.format(name, info['type']) + '\n')

    def _get_fn_name_locals(self):
        for fn_name, info in self.local_vars.items():
            if info['from_lineno'] < self.line_no < info['to_lineno']:
                return fn_name, info['variables']
        return '', {}

    def do_locals(self, *args):
        if not self.local_vars:
            self.stdout.write('No locals found.\n')
        fn_name, variables = self._get_fn_name_locals()
        self.stdout.write('Function: {}'.format(fn_name) + '\n')
        self.stdout.write('Name\t\tType' + '\n')
        for name, info in variables.items():
            self.stdout.write('{}\t\t{}'.format(name, info['type']) + '\n')

    def completenames(self, text, *ignored):
        line = text.strip()
        if 'self.' in line:
            return [
                'self.' + x
                for x in self.globals.keys()
                if x.startswith(line.split('self.')[1])
            ]
        else:
            dotext = 'do_' + text
            cmds = [a[3:] for a in self.get_names() if a.startswith(dotext)]
            _, local_vars = self._get_fn_name_locals()
            return cmds + [x for x in local_vars.keys() if x.startswith(line)]

    def mload(self, line):
        """ Read something from memory """
        pos = line.strip()
        self.stdout.write(to_hex(to_hex(self.computation.memory_read(pos, 32))))

    def default(self, line):
        line = line.strip()
        fn_name, local_variables = self._get_fn_name_locals()

        if line.startswith('self.') and len(line) > 4:
            parse_global(
                self.stdout, self.global_vars, self.computation, line
            )
        elif line in local_variables:
            parse_local(
                self.stdout, local_variables, self.computation, line
            )
        else:
            self.stdout.write('*** Unknown syntax: %s\n' % line)

    def do_stack(self, *args):
        """ Show contents of the stack """
        for idx, value in enumerate(self.computation._stack.values):
            self.stdout.write("{}\t{}".format(idx, to_hex(value)) + '\n')
        else:
            self.stdout.write("Stack is empty\n")

    def do_pdb(self, *args):
        # Break out to pdb for vdb debugging.
        import pdb; pdb.set_trace()  # noqa

    def do_history(self, *args):
        history(self.stdout)

    def emptyline(self):
        pass

    def do_quit(self, *args):
        return True

    def do_exit(self, *args):
        """ Exit vdb """
        return True

    def do_continue(self, *args):
        """ Exit vdb """
        return True

    def do_EOF(self, line):
        """ Exit vdb """
        return True


original_opcodes = evm.vm.forks.byzantium.computation.ByzantiumComputation.opcodes


def set_evm_opcode_debugger(source_code=None, source_map=None, stdin=None, stdout=None):

    def debug_opcode(computation):
        line_no = computation.stack_pop(num_items=1, type_hint=constants.UINT256)
        VyperDebugCmd(
            computation,
            line_no=line_no,
            source_code=source_code,
            source_map=source_map,
            stdin=stdin,
            stdout=stdout
        ).cmdloop()

    opcodes = original_opcodes.copy()
    opcodes[vyper_opcodes['DEBUG'][0]] = as_opcode(
        logic_fn=debug_opcode,
        mnemonic="DEBUG",
        gas_cost=0
    )

    setattr(evm.vm.forks.byzantium.computation.ByzantiumComputation, 'opcodes', opcodes)


def set_evm_opcode_pass():

    def debug_opcode(computation):
        computation.stack_pop(num_items=1, type_hint=constants.UINT256)

    opcodes = original_opcodes.copy()
    opcodes[vyper_opcodes['DEBUG'][0]] = as_opcode(
        logic_fn=debug_opcode,
        mnemonic="DEBUG",
        gas_cost=0
    )
    setattr(evm.vm.forks.byzantium.computation.ByzantiumComputation, 'opcodes', opcodes)
