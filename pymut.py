import inspect
import ast
import codegen
import signal
import time
import math
import sys
import textwrap
import pdb

def handler(signum, frame):
    raise Exception()
    
class Nil:
    def __init__(self):
        pass

class Blackhole(object):
    def write(self, string):
        pass

class Mutator:
    ARITH_OP = {ast.Sub: ast.Sub(), ast.Add: ast.Add(), ast.Div: ast.Div(), ast.Mult: ast.Mult()}
    
    CMP_OP = {ast.Eq: ast.Eq(), ast.Gt: ast.Gt(), ast.Lt: ast.Lt(), ast.GtE: ast.GtE(), ast.LtE: ast.LtE(), ast.NotEq: ast.NotEq()}
    
    absolute = 1
    relative = 2
    
    low = [False, True, False, False, True, False, False]
    midium = [False, True, False, False, True, False, True]
    high = [True]*7
    
    bh = Blackhole()
    Nil = Nil()
    
    def __init__(self, g, tol = 2, mutations = high):
        self.gamma = g
        if tol == Mutator.absolute:
            self.tolerance = self.abs_tol
        else:
            self.tolerance = self.rel_tol
        self.__mutations__ = mutations
    
    def mutate_tree(self, tree):
        for node in ast.walk(tree):
            if hasattr(node, 'body') and self.__mutations__[0]:
                for n in range(0, len(node.body)):
                    if (isinstance(node.body[n],ast.If) or 
                            isinstance(node.body[n],ast.While) or 
                            isinstance(node.body[n],ast.For) or 
                            isinstance(node.body[n],ast.Assign)):
                        temp = node.body[n]
                        node.body[n] = ast.Pass()
                        yield tree
                        node.body[n] = temp
            if isinstance(node,ast.Num) and self.__mutations__[1]:
                nt = node.n
                node.n = 0
                yield tree
                node.n = nt*-1
                yield tree
                node.n = nt+1
                yield tree
                node.n = nt-1
                yield tree
                node.n = nt*0.9
                yield tree
                node.n = nt*1.1
                yield tree
                node.n = nt
            elif isinstance(node,ast.If) or isinstance(node,ast.While) and self.__mutations__[3]:
                test = node.test
                uo = ast.UnaryOp()
                uo.op = ast.Not()
                uo.operand = test
                node.test = uo
                yield tree
                if isinstance(node,ast.If) and self.__mutations__[2]:
                    uo = ast.Name("True",ast.Load())
                    node.test = uo
                    yield tree
                    body = list(node.body)
                    orelse = list(node.orelse)
                    node.body+=node.orelse
                    node.oerlse = []
                    yield tree
                    node.body = body
                    node.oerlse = orelse
                    uo = ast.Name("False",ast.Load())
                    node.test = uo
                    yield tree
                node.test = test
            elif isinstance(node,ast.BinOp) and self.__mutations__[4]:
                original = node.op
                if type(original) in Mutator.ARITH_OP:
                    m = Mutator.ARITH_OP
                else:
                    continue
                for op in m.keys():
                    if op != type(original):
                        node.op = m[op]
                        yield tree
                        node.op = original
            elif isinstance(node,ast.BoolOp) and self.__mutations__[5]:
                for i in range(0,len(node.values)):
                    v = node.values[i]
                    uo = ast.UnaryOp()
                    uo.op = ast.Not()
                    uo.operand = v
                    node.values[i] = uo
                    yield tree
                    node.values[i] = v
                if type(node.op) == ast.Or:
                    node.op = ast.And()
                    yield tree
                    node.op = ast.Or()
                else:
                    node.op = ast.Or()
                    yield tree
                    node.op = ast.And()
            elif isinstance(node,ast.Compare) and self.__mutations__[6]:
                original = node.ops[0]
                if type(original) in Mutator.CMP_OP:
                    m = Mutator.CMP_OP
                else:
                    continue
                for op in m.keys():
                    if op != type(original):
                        node.ops[0] = m[op]
                        yield tree
                        node.ops[0] = original
                

    def mutate_func(self, f):
        s = inspect.getsource(f)
        tree = ast.parse(textwrap.dedent(s))
        for tree2 in self.mutate_tree(tree):
            yield codegen.to_source(tree2)
    
    def abs_tol(self, mut_res, orig_res):
        return math.fabs(mut_res - orig_res) > self.gamma
    
    def rel_tol(self, mut_res, orig_res):
        return math.fabs((mut_res - orig_res*1.0)/orig_res) > self.gamma

    def sceilent_run(self, f, inp):
        try:
            sys.stdout = Mutator.bh
            sys.stderr = Mutator.bh
            r = f(*inp)
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
        except:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            r = Mutator.Nil
        return r
        
    def test(self, f, test_sets, mut_funcs=[]):
        #pdb.set_trace()
        signal.signal(signal.SIGALRM, handler)
        original_res = []
        bad_mutants = []
        total_mutants = 0
        done = [True]*len(test_sets)
        i = -1
        runtime = []
        for test_set in test_sets:
            i = i+1
            start = time.time()
            r = self.sceilent_run(f, test_set)
            original_res.append(r)
            if r == Mutator.Nil:
                done[i] = False
                print >> sys.stderr, "Could not run function ",f.__name__, " on input ", test_set
                continue
            """try:
                sys.stdout = bh
                sys.stderr = bh
                original_res.append(f(*test_set))
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
            except:
                done[i] = False
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                print >> sys.stderr, "Could not run function ",f.__name__, " on imput ", test_set
                original_res.append(None)
                continue"""
            runtime.append(time.time() - start)
        if done.count(True)==0:
            print >> sys.stderr, "could not run any test case on ",f.__name__
            return []
        for m_func in [f]+mut_funcs:
            for mutant in self.mutate_func(m_func):
                total_mutants = total_mutants+1
                i = 0
                try:
                    exec mutant
                except:
                    print """Malformated mutant"""
                    total_mutants = total_mutants-1
                    continue
                original_func = m_func
                if inspect.ismethod(m_func):
                    m_func.im_class.__dict__[m_func.__name__] = locals()[m_func.__name__]
                else:
                    inspect.getmodule(m_func).__dict__[m_func.__name__] = locals()[m_func.__name__]
                ind = -1
                for test_set in test_sets:
                    ind = ind+1
                    if done[ind]:
                        signal.alarm(int(math.ceil(3*runtime[i])))
                        res = self.sceilent_run(locals()[f.__name__], test_set)
                        if res == Mutator.Nil:
                            print "Mutant takes too long ... Killed"
                            signal.alarm(0)
                            continue
                        """try:
                            sys.stdout = bh
                            sys.stderr = bh
                            res = locals()[f.__name__](*test_set)
                            sys.stdout = sys.__stdout__
                            sys.stderr = sys.__stderr__
                        except:
                            sys.stdout = sys.__stdout__
                            sys.stderr = sys.__stderr__
                            print "Mutant takes too long ... Killed"
                            signal.alarm(0)
                            continue"""
                        signal.alarm(0)
                        if (type(res) != type(original_res[i]) or
                               ((type(res) == int or type(res) == float) and 
                               self.tolerance(res, original_res[i]))
                               or (type(res) != int and type(res) != float and res != original_res[i])):
                            print """Mutant discarded ..."""
                            break
                        i = i+1
                else:
                    print """Mutant passes all tests ..."""
                    bad_mutants.append(mutant)
                if inspect.ismethod(m_func):
                    m_func.im_class.__dict__[m_func.__name__] = original_func
                else:
                    inspect.getmodule(m_func).__dict__[m_func.__name__] = original_func
                locals()[f.__name__] = f
        print total_mutants, " mutations tested"
        if total_mutants >0:
            print "percentage of detected mutants = ", ((total_mutants-len(bad_mutants))*100.0)/total_mutants, "%"
        return bad_mutants
        
