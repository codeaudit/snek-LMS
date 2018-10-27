from pylms import *
from pylms.rep import *
from pylms.nn_staging import *

@lms
def run(x):
  def power(n, k):
    while k > 0:
      n = n * k
      k = k - 1
    # if k == 0:
    #   return 1
    # else:
    #   return n * \
    #     power(n, k - 1)
  res = power(x, 2)
  return res

print("======= Original code =======")
print(run.original_src)
print("======= Converted code ========")
print(run.src)
print("\n")

@stage
def runX(x):
  return run(x)

print("======= SExpr ========")
print(runX.code)
print("\n")
print("======= C/C++ code ========")
print(runX.Ccode)
print(runX(2))