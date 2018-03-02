#/usr/bin/python3

import sys
import ast
import types
import parser
import inspect
import builtins
import virtualized

def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer

################################################

class IR(object): pass

class IRConst(IR):
    def __init__(self, v):
        self.v = v

class IRInt(IR):
    def __init__(self, n):
        self.n = n

class IRIntAdd(IR):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

class IRIntMul(IR):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

class IRIf(IR):
    def __init__(self, cnd, thn, els): NotImplemented

class IRRet(IR):
    def __init__(self, val): NotImplemented

################################################

class PyGenIRConst(object):
    def gen(self, irconst): return str(irconst.v)

class PyGenIRInt(object):
    def gen(self, irint): return str(irint.n)

class PyGenIRIntAdd(object):
    def gen(self, iradd):
        lhscode = PyCodeGen(iradd.lhs).gen()
        rhscode = PyCodeGen(iradd.rhs).gen()
        return "{0} + {1}".format(lhscode, rhscode)

class PyGenIRIntMul(object):
    def gen(self, irmul):
        lhscode = PyCodeGen(irmul.lhs).gen()
        rhscode = PyCodeGen(irmul.rhs).gen()
        return "{0} * {1}".format(lhscode, rhscode)

class CodeGen(object): pass

class PyCodeGen(CodeGen):
    def __init__(self, ir):
        self.ir = ir
    def gen(self):
        clsName = "PyGen{0}".format(type(self.ir).__name__)
        modl = sys.modules[__name__]
        Cls = getattr(modl, clsName)
        return Cls().gen(self.ir)

class CCodeGen(CodeGen): pass

################################################

class RepTyp(object): pass

class RepInt(RepTyp):
    def __init__(self, n):
        self.n = n
    def __IR__(self):
        if isinstance(self.n, int): return IRConst(self.n)
        else: return IRInt(self.n)
    def __add__(self, m):
        if isinstance(m, RepTyp): m = m.__IR__()
        return IRIntAdd(self.__IR__(), m)
    def __mul__(self, m):
        if isinstance(m, RepTyp): m = m.__IR__()
        return IRIntMul(self.__IR__(), m)

################################################

class RepFunc():
    def __init__(self, func, *args, **kwargs):
        self.func = func
        #TODO

class CompiledCode:
    def __init__(self):
        pass

class StagingRewriter(ast.NodeTransformer):
    """
    StagingRewriter does two things:
    1) lift next-stage variables to be Rep
    2) virtualize primitives such as `if`, `while`, `for` and etc
    Note: Probably we may also rewrite operators such as `+` rather than overloading them.
    """
    def __init__(self, reps):
        self.reps = reps
        super()

    def visit_If(self, node):
        # TODO: Virtualization of `if`
        # If the condition part relies on a staged value, then it should be virtualized.
        # print(ast.dump(node))

        # if node is of the form (test, body, orelse)

        # iter_fields lets me iterate through the contents of the if node
        # gives the child as a tuple of the form (child-type, object)
        print(ast.dump(node))
        # print(ast.dump(node.test))
        # print("iffff")
        cond_node = node.test;
        # check for BoolOp and then Compare

        x = ast.Call(func=ast.Name('__if', ast.Load()), args=[node.test, node.body, node.orelse], keywords=[])
        print("defined x")
        print(ast.dump(x))

        self.generic_visit(node)
        return node

    def visit_While(self, node):
        # TODO: Virtualization of `while`
        # print("while")
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        # Drop the decorator
        self.generic_visit(node)
        node.decorator_list = []
        return node

    def visit_Return(self, node):
        self.generic_visit(node)
        # TODO: just a poor hack to make power work
        if ast.dump(node.value) == ast.dump(ast.Num(1)):
            ret = ast.copy_location(ast.Return(value=ast.Call(func=ast.Name(id='RepInt', ctx=ast.Load()),
                                                               args=[ast.Num(1)],
                                                               keywords=[])),
                                     node)

            return ret
        return node

    def visit_Name(self, node):
        self.generic_visit(node)
        if node.id in self.reps:
            return ast.copy_location(ast.Call(func=ast.Name(id=self.reps[node.id].__name__, ctx=ast.Load()),
                                              args=[ast.Str(s=node.id)],
                                              keywords=[]),
                                    node)
        return node

@parametrized
def lms(obj, *args, **kwargs):
    """
    Rep transforms the AST to annotated AST with Rep(s).
    TODO: What about Rep values defined inside of a function, rather than as an argument?
    TODO: How to lift constant value?
    TODO: How to handle `return`
    TODO: Handle sequence and side effects
    TODO: Assuming that there is no free variables in the function
    """
    if isinstance(obj, types.FunctionType):
        func = obj
        func_ast = ast.parse(inspect.getsource(func))
        # for n in ast.walk(func_ast):
            # if isinstance(n, ast.If):
                # print(ast.dump(n))
        new_func_ast = StagingRewriter(kwargs).visit(func_ast)
        ast.fix_missing_locations(new_func_ast)
        exec(compile(new_func_ast, filename="<ast>", mode="exec"), globals())
        return eval(func.__name__)
    elif isinstance(obj, types.MethodType):
        return NotImplemented
    else: return NotImplemented

@parametrized
def Specalize(f, Codegen, *args, **kwargs):
    """
    Specalize transforms the annotated IR to target language.
    Note: f must be a named function
    TODO: f's argument names may different with variables in the inner body
    """
    fun_name = f.__name__
    fun_args = inspect.getargspec(f).args
    rep_args = [kwargs[fa](fa) for fa in fun_args]
    irbody = f(*rep_args)
    codegen = Codegen(irbody)
    codestr = "def {0}({1}): return {2}".format(fun_name, ','.join(fun_args), codegen.gen())
    exec(codestr, globals())
    return eval(fun_name)

################################################

def giveBack(x):
    return x
"""
TODO: Does user need to provide Rep annotation on returned value?
"""
@lms(b = RepInt)
def power(b, x):
    y = x
    while (y > 0):
        y = y - 1
    if (x == 0): return 1
    else: return b * power(b, x-1)

"""
Explaination: intuitively, the instrumented AST of `power` looks like `stagedPower`.
`if` is a current-stage expression, so it is not virtualized, and will be executed as normal code.
But `b` is a next-stage variable, so it became `RepInt(b)`. `1` also lifted to `RepInt(1)`
because we (implicitly) require that the types of both branches should same.
`*` __mul__ operator should be overloaded by RepInt.
By running `stagedPower`, we obtain the IR that will be used later by code generator.
"""
def stagedPower(b, x):
    if (x == 0): return RepInt(1)
    else: return RepInt("b") * stagedPower(RepInt("b"), x - 1)

################################################

"""
Ideally, user could specify different code generators for different targer languages.
The code generator translates IR to string representation of target language.
"""
@Specalize(PyCodeGen, b = RepInt)
def snippet(b):
    return power(b, 3)

assert(snippet(3) == 27) # Here we can just use snippet

"""
Explaination: decorating `snippet` with @Specalize is equivalent to:
"""
def snippet2(b): return stagedPower(b, 3)
power3 = Specalize(PyCodeGen, b = RepInt)(snippet2)
assert(power3(3) == 27)