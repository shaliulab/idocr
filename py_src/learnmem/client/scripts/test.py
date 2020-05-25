mylist = [[1,], [2,]]

def myfunc(x):
    x.append(x[0]+10)


for e in mylist:
    myfunc(e)

print(mylist)

