def item_splitpath(path):
    name, _, attr = path.partition(".")
    attr, _, _ = attr.partition(".")
    return name, attr


def get_item_type(path):
    n, _ = item_splitpath(path)
    return n


def item_attr(path):
    _, p = item_splitpath(path)
    return p
