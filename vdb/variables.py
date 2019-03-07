from eth_hash.auto import keccak
from eth_abi import decode_single
from eth_utils import (
    to_hex,
    big_endian_to_int,
    int_to_big_endian,
)
from vyper.utils import ceil32


base_types = (
    'int128',
    'uint256',
    'address',
    'bytes32'
)


def print_var(stdout, value, var_typ):

    if isinstance(value, int):
        v = int_to_big_endian(value)
    else:
        v = value

    if isinstance(v, bytes):
        if var_typ in ('int128', 'uint256'):
            if len(v) < 32:
                v = v.rjust(32, b'\0')
            stdout.write(str(decode_single(var_typ, v)) + '\n')
        elif var_typ == 'address':
            stdout.write(to_hex(v[12:]) + '\n')
        elif var_typ.startswith('bytes'):
            stdout.write(str(v) + '\n')
        elif var_typ.startswith('string'):
            stdout.write(v.decode() + '\n')
    else:
        stdout.write(v.decode() + '\n')


def parse_local(stdout, local_variables, computation, line):
    var_info = local_variables[line]
    local_type = var_info['type']
    if local_type in base_types:
        start_position = var_info['position']
        value = computation.memory_read(start_position, 32)
        print_var(stdout, value, local_type)
    elif local_type.startswith('bytes') or local_type.startswith('string'):
        start_position = var_info['position']
        byte_len = big_endian_to_int(computation.memory_read(start_position, 32))
        if byte_len == 0:
            stdout.write("(empty)\n")
        value = computation.memory_read(start_position + 32, byte_len)
        print_var(stdout, value, local_type)
    else:
        stdout.write('Can not read local of type "{}" \n'.format(local_type))


def get_keys(n):
    out = []
    name = n
    for _ in range(name.count('[')):
        open_pos = name.find('[')
        close_pos = name.find(']')
        key = name[open_pos + 1:close_pos].replace('\'', '').replace('"', '')
        name = name[close_pos + 1:]
        out.append(key)
    return out


def get_hash(var_pos, keys, _type):
    key_inp = b''

    key_inp = keccak(
        int_to_big_endian(var_pos).rjust(32, b'\0') +
        keys[0].encode().ljust(32, b'\0')
    )
    for key in keys[1:]:
        key_inp = keccak(key_inp + key.encode().ljust(32, b'\0'))
    slot = big_endian_to_int(key_inp)
    return slot


def valid_subscript(name, global_type):
    if name.count('[') != name.count(']'):
        return False
    elif global_type.count('(') != name.count(']'):
        return False
    return True


def parse_global(stdout, global_vars, computation, line):
    # print global value.
    name = line.split('.')[1]
    var_name = name[:name.find('[')] if '[' in name else name

    if var_name not in global_vars:
        stdout.write('Global named "{}" not found.'.format(var_name) + '\n')
        return

    global_type = global_vars[var_name]['type']
    slot = None
    size = global_vars[var_name]['size']
    is_bytelike = global_type.startswith('bytes') or global_type.startswith('string')

    if global_type in base_types or is_bytelike:
        slot = global_vars[var_name]['position']
    elif global_type.startswith('map') and valid_subscript(name, global_type):
        keys = get_keys(name)
        var_pos = global_vars[var_name]['position']
        slot = get_hash(var_pos, keys, global_type)

    if slot is not None:
        if is_bytelike:
            value = b""
            base_slot_hash = big_endian_to_int(keccak(int_to_big_endian(slot).rjust(32, b'\0')))
            len_val = computation.state.account_db.get_storage(
                address=computation.msg.storage_address,
                slot=base_slot_hash,
            )
            for i in range(0, ceil32(len_val) // 32):
                sub_slot = base_slot_hash + 1 + i
                value += int_to_big_endian(
                    computation.state.account_db.get_storage(
                    address=computation.msg.storage_address,
                    slot=sub_slot,
                    )
                )
            value = value[:len_val]
        else:
            value = computation.state.account_db.get_storage(
                address=computation.msg.storage_address,
                slot=slot,
            )
        if global_type.startswith('map'):
            global_type = global_type[global_type.rfind(',') + 1: global_type.rfind(')')].strip()
        print_var(stdout, value, global_type)
    else:
        stdout.write('Can not read global of type "{}".\n'.format(global_type))
