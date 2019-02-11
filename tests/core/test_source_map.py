from vdb.source_map import produce_source_map


def test_source_map_output():
    code = """
a_map: map(bytes32, bytes32)

@public
def func1(a: int128) -> int128:
    b: int128 = 2
    c: int128 = 3
    g: bytes[10]
    return a + b + c + 1

@public
def func2(a: int128):
    x: uint256
    """

    sm = produce_source_map(code)

    # globals
    assert sm['globals']['a_map'] == {
        'type': 'map(bytes32, bytes32)',
        'size': 0,
        'position': 0
    }

    # locals
    assert sm['locals']['func1'] == {
        'from_lineno': 4,
        'to_lineno': 11,
        'variables': {
            'a': {'type': 'int128', 'size': 32, 'position': 320},
            'b': {'type': 'int128', 'size': 32, 'position': 352},
            'c': {'type': 'int128', 'size': 32, 'position': 384},
            'g': {'type': 'bytes[10]', 'size': 96, 'position': 416}
        },
    }
