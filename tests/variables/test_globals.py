import io


def test_single_key(get_contract, get_last_out):
    code = """
amap: map(bytes32, bytes32)


@public
def set(key: bytes32, value: bytes32):
    self.amap[key] = value


@public
def get(key: bytes32) -> bytes32:
    vdb
    return self.amap[key]
    """

    stdin = io.StringIO(
        "self.amap['one']\n"
    )
    stdout = io.StringIO()
    c = get_contract(code, stdin=stdin, stdout=stdout)
    c.functions.set(b'one', b'hello!').transact()
    res = c.functions.get(b'one').call({'gas': 600000})

    assert res[:6] == b'hello!'
    assert 'hello!' in stdout.getvalue()


def test_double_key(get_contract, get_last_out):
    code = """
amap: map(bytes32, map(bytes32, bytes32))

@public
def set(key1: bytes32, key2: bytes32, value: bytes32):
    self.amap[key1][key2] = value


@public
def get(key1: bytes32, key2: bytes32) -> bytes32:
    vdb
    return self.amap[key1][key2]
    """

    stdin = io.StringIO(
        "self.amap[one][two]\n"
    )
    stdout = io.StringIO()
    c = get_contract(code, stdin=stdin, stdout=stdout)
    c.functions.set(b'one', b'two', b'hello!').transact()
    res = c.functions.get(b'one', b'two').call({'gas': 600000})

    assert res[:6] == b'hello!'
    assert 'hello!' in stdout.getvalue()
