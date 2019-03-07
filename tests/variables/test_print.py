import io


def test_print_uint256(get_contract, get_last_out):
    code = """
@public
def test():
    a: uint256 = 33343
    vdb
    a = 2
    """

    stdin = io.StringIO(
        "a\n"
    )
    stdout = io.StringIO()

    c = get_contract(code, stdin=stdin, stdout=stdout)
    c.functions.test().transact({"gas": 22000})

    assert get_last_out(stdout) == '33343'


def test_print_int128(get_contract, get_last_out):
    code = """
@public
def test():
    a: int128 = -123
    vdb
    a = 2
    """

    stdin = io.StringIO(
        "a\n"
    )
    stdout = io.StringIO()

    c = get_contract(code, stdin=stdin, stdout=stdout)
    c.functions.test().transact({"gas": 22000})

    assert get_last_out(stdout) == '-123'


def test_print_string_from_storage(get_contract, get_last_out):
    code = """
car: public(string[64])

@public
def getCar() -> string[64]:
    self.car = "My little car!"
    vdb
    return self.car
    """

    stdin = io.StringIO(
        "self.car\n"
    )
    stdout = io.StringIO()

    c = get_contract(code, stdin=stdin, stdout=stdout)
    c.functions.getCar().call({"gas": 92000})

    assert get_last_out(stdout) == "My little car!"
