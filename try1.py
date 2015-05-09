class Foo:
    def foo(self, a, b):
        temp = a
        while (a<b):
            a = a+1
        a = a+temp
        i = 1
        j = 2
        k = 3
        if a < b or a+b > 10:
            i = 2 * i
        elif b<a or False:
            print "b < a"
        else:
            print "="
        return i+j+k+a+b+4
        
    def k(self,a,b):
        if True:
            return self.foo(a,b)

def tt(a,b):
    return Foo().foo(a,b)
