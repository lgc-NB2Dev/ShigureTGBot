from copy import deepcopy


def split_list(li: list, length: int):
    latest = []
    tmp = []
    for n, i in enumerate(li):
        tmp.append(i)
        if (n + 1) % length == 0:
            latest.append(deepcopy(tmp))
            tmp.clear()
    latest.append(deepcopy(tmp))
    return latest
