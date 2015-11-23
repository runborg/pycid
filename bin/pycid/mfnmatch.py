from fnmatch import fnmatch

#class mfnmatch(object):
def longest(string, matches):
    """
    Search string for matching fnmatch
    Returns the longest match when a string is matched by several fnmatch searches 
    >>> longest_match("string", ["str*", "stri??"])
    stri??

    """
    try :return max([m for m in matches if fnmatch(string, m)], key=len)
    except: return None
def matches(string, matches):
    """
    Search string for matching fnmatch
    Returns a list with all matches when a string is matched by several fnmatch searches
    >>> matches("string", ["str*", "stri??", "namat?h"]
    ["str*", "stri??"]
    
    """
    return [m for m in matches if fnmatch(string, m)]


