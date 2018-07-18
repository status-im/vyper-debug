import cmd

# from eth_hash.auto import keccak
from eth_utils import to_hex
from eth_abi import decode_single

import evm
from evm import constants
from evm.vm.opcode import as_opcode
from evm.utils.numeric import (
    int_to_big_endian,
)
from vyper.opcodes import opcodes as vyper_opcodes

commands = [
    'continue',
    'locals',
    'globals'
]
base_types = ('int128', 'uint256', 'address', 'bytes32')


def history(stdout):
    import readline
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


def print_var(stdout, value, var_typ):

    if isinstance(value, int):
        v = int_to_big_endian(value)
    else:
        v = value

    if isinstance(v, bytes):
        if var_typ in ('int128', 'uint256'):
            stdout.write(str(decode_single(var_typ, value)) + '\n')
        elif var_typ == 'address':
            stdout.write(to_hex(v[12:]) + '\n')
    else:
        stdout.write(v + '\n')


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
        self.globals = source_map.get("globals")
        self.locals = source_map.get("locals")
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
        if not self.globals:
            self.stdout.write('No globals found.' + '\n')
        self.stdout.write('Name\t\tType' + '\n')
        for name, info in self.globals.items():
            self.stdout.write('self.{}\t\t{}'.format(name, info['type']) + '\n')

    def _get_fn_name_locals(self):
        for fn_name, info in self.locals.items():
            if info['from_lineno'] < self.line_no < info['to_lineno']:
                return fn_name, info['variables']
        return '', {}

    def do_locals(self, *args):
        if not self.locals:
            self.stdout.write('No locals found.\n')
        fn_name, variables = self._get_fn_name_locals()
        self.stdout.write('Function: {}'.format(fn_name) + '\n')
        self.stdout.write('Name\t\tType' + '\n')
        for name, info in variables.items():
            self.stdout.write('{}\t\t{}'.format(name, info['type']) + '\n')

    def default(self, line):
        fn_name, local_variables = self._get_fn_name_locals()

        if line.startswith('self.') and len(line) > 4:
            if not self.globals:
                self.stdout.write('No globals found.' + '\n')
            # print global value.
            name = line.split('.')[1]
            if name not in self.globals:
                self.stdout.write('Global named "{}" not found.'.format(name) + '\n')
            else:
                global_type = self.globals[name]['type']
                slot = None

                if global_type in base_types:
                    slot = self.globals[name]['position']
                elif global_type == 'mapping':
                    # location_hash= keccak(int_to_big_endian(
                    #    self.globals[name]['position']).rjust(32, b'\0'))
                    # slot = big_endian_to_int(location_hash)
                    pass
                else:
                    self.stdout.write('Can not read global of type "{}".\n'.format(global_type))

                if slot is not None:
                    value = self.computation.state.account_db.get_storage(
                        address=self.computation.msg.storage_address,
                        slot=slot,
                    )
                    print_var(self.stdout, value, global_type)
        elif line in local_variables:
            var_info = local_variables[line]
            local_type = var_info['type']
            if local_type in base_types:
                start_position = var_info['position']
                value = self.computation.memory_read(start_position, 32)
                print_var(self.stdout, value, local_type)
            else:
                self.stdout.write('Can not read local of type\n')
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
