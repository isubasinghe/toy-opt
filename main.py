from typing import Optional, Any, List


class Value:
    def find(self):
        raise NotImplementedError("abstract")
    def _set_forwarded(self, value):
        raise NotImplementedError("abstract")


class Operation(Value):
    def __init__(self, name: str, args: List[Value]):
        self.name = name
        self.args = args
        self.forwarded = None

    def __repr__(self):
        return (
            f"Operation({self.name},"
            f"{self.args}, {self.forwarded})"
        )

    def find(self) -> Value:
        # returns the "representative" value of
        # self, in the union-find sense
        op = self
        while isinstance(op, Operation):
            # could do path compression here too
            # but not essential
            next = op.forwarded
            if next is None:
                return op
            op = next
        return op

    def arg(self, index):
        # change to above: return the
        # representative of argument 'index'
        return self.args[index].find()

    def make_equal_to(self, value: Value):
        # this is "union" in the union-find sense,
        # but the direction is important! The
        # representative of the union of Operations
        # must be either a Constant or an operation
        # that we know for sure is not optimized
        # away.

        self.find()._set_forwarded(value)

    def _set_forwarded(self, value: Value):
        self.forwarded = value


class Constant(Value):
    def __init__(self, value: Any):
        self.value = value

    def __repr__(self):
        return f"Constant({self.value})"

    def find(self):
        return self

    def _set_forwarded(self, value: Value):
        # if we found out that an Operation is
        # equal to a constant, it's a compiler bug
        # to find out that it's equal to another
        # constant
        assert isinstance(value, Constant) and \
            value.value == self.value


class Block(list):
    def opbuilder(opname: str):
        def wraparg(arg):
            if not isinstance(arg, Value):
                arg = Constant(arg)
            return arg 

        def build(self, *args):
            op = Operation(opname, [wraparg(arg) for arg in args])
            self.append(op)
            return op
        return build

    add = opbuilder("add")
    mul = opbuilder("mul")
    getarg = opbuilder("getarg")
    dummy = opbuilder("dummy")
    lshift = opbuilder("lshift")

def test_convencience_block_construction():
    bb = Block()
    # a again with getarg, the following line
    # defines the Operation instance and
    # immediately adds it to the basic block bb
    a = bb.getarg(0)
    assert len(bb) == 1
    assert bb[0].name == "getarg"

    # it's a Constant
    assert bb[0].args[0].value == 0

    # b with getarg
    b = bb.getarg(1)
    # var1 = add(b, 17)
    var1 = bb.add(b, 17)
    # var2 = mul(a, var1)
    var2 = bb.mul(a, var1)
    # var3 = add(b, 17)
    var3 = bb.add(b, 17)
    # var4 = add(var2, var3)
    var4 = bb.add(var2, var3)
    assert len(bb) == 6

def bb_to_str(bb: Block, varprefix: str = "var"):
    # the implementation is not too important,
    # look at the test below to see what the
    # result looks like

    def arg_to_str(arg: Value):
        if isinstance(arg, Constant):
            return str(arg.value)
        else:
            # the key must exist, otherwise it's
            # not a valid SSA basic block:
            # the variable must be defined before
            # its first use
            return varnames[arg]

    varnames = {}
    res = []
    for index, op in enumerate(bb):
        # give the operation a name used while
        # printing:
        var = f"{varprefix}{index}"
        varnames[op] = var
        arguments = ", ".join(
            arg_to_str(op.arg(i))
                for i in range(len(op.args))
        )
        strop = f"{var} = {op.name}({arguments})"
        res.append(strop)
    return "\n".join(res)

def test_basicblock_to_str():
    bb = Block()
    var0 = bb.getarg(0)
    var1 = bb.add(5, 4)
    var2 = bb.add(var1, var0)

    assert bb_to_str(bb) == """\
var0 = getarg(0)
var1 = add(5, 4)
var2 = add(var1, var0)"""

    # with a different prefix for the invented
    # variable names:
    assert bb_to_str(bb, "x") == """\
x0 = getarg(0)
x1 = add(5, 4)
x2 = add(x1, x0)"""

    # and our running example:
    bb = Block()
    a = bb.getarg(0)
    b = bb.getarg(1)
    var1 = bb.add(b, 17)
    var2 = bb.mul(a, var1)
    var3 = bb.add(b, 17)
    var4 = bb.add(var2, var3)

    assert bb_to_str(bb, "v") == """\
v0 = getarg(0)
v1 = getarg(1)
v2 = add(v1, 17)
v3 = mul(v0, v2)
v4 = add(v1, 17)
v5 = add(v3, v4)"""

def test_union_find():
    # construct three operation, and unify them
    # step by step
    bb = Block()
    a1 = bb.dummy(1)
    a2 = bb.dummy(2)
    a3 = bb.dummy(3)

    # at the beginning, every op is its own
    # representative, that means every
    # operation is in a singleton set
    # {a1} {a2} {a3}
    assert a1.find() is a1
    assert a2.find() is a2
    assert a3.find() is a3

    # now we unify a2 and a1, then the sets are
    # {a1, a2} {a3}
    a2.make_equal_to(a1)
    # they both return a1 as the representative
    assert a1.find() is a1
    assert a2.find() is a1
    # a3 is still different
    assert a3.find() is a3

    # now they are all in the same set {a1, a2, a3}
    a3.make_equal_to(a2)
    assert a1.find() is a1
    assert a2.find() is a1
    assert a3.find() is a1

    # now they are still all the same, and we
    # also learned that they are the same as the
    # constant 6
    # the single remaining set then is
    # {6, a1, a2, a3}
    c = Constant(6)
    a2.make_equal_to(c)
    assert a1.find() is c
    assert a2.find() is c
    assert a3.find() is c

    # union with the same constant again is fine
    a2.make_equal_to(c)

if __name__ == '__main__':
    print("---PyOpt---")
    test_convencience_block_construction()
    test_basicblock_to_str()
    test_union_find()
