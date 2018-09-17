from vyper.parser import (
    parser,
)
from vyper.parser.global_context import (
    GlobalContext
)
from vyper.types import (
    get_size_of_type,
    ByteArrayType,
    MappingType,
    TupleType
)


def serialise_var_rec(var_rec):
    if isinstance(var_rec.typ, ByteArrayType):
        type_str = 'bytes[%s]' % var_rec.typ.maxlen
        _size = get_size_of_type(var_rec.typ) * 32
    elif isinstance(var_rec.typ, TupleType):
        type_str = 'tuple'
        _size = get_size_of_type(var_rec.typ) * 32
    elif isinstance(var_rec.typ, MappingType):
        type_str = 'mapping(%s)' % var_rec.typ
        _size = 0
    else:
        type_str = var_rec.typ.typ
        _size = get_size_of_type(var_rec.typ) * 32

    out = {
        'type': type_str,
        'size': _size,
        'position': var_rec.pos
    }
    return out


def produce_source_map(code):
    global_ctx = GlobalContext.get_global_context(parser.parse(code))
    source_map = {
        'globals': {},
        'locals': {}
    }
    source_map['globals'] = {
        name: serialise_var_rec(var_record)
        for name, var_record in global_ctx._globals.items()
    }
    # Fetch context for each function.
    lll = parser.parse_tree_to_lll(parser.parse(code), code, runtime_only=True)
    contexts = {
        f.func_name: f.context
        for f in lll.args[1:] if hasattr(f, 'context')
    }

    prev_func_name = None
    for _def in global_ctx._defs:
        if _def.name != '__init__':
            func_info = {
                'from_lineno': _def.lineno,
                'variables': {}
            }
            # set local variables for specific function.
            context = contexts[_def.name]
            func_info['variables'] = {
                var_name: serialise_var_rec(var_rec)
                for var_name, var_rec in context.vars.items()
            }

            source_map['locals'][_def.name] = func_info
            # set to_lineno
            if prev_func_name:
                source_map['locals'][prev_func_name]['to_lineno'] = _def.lineno
            prev_func_name = _def.name

    source_map['locals'][_def.name]['to_lineno'] = len(code.splitlines())

    return source_map
