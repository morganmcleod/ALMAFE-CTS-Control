import re
from typing import List

DEFAULT_DELIMS = r'[,"\s\r\n]'

def removeDelims(data: str, delimsRe: str = DEFAULT_DELIMS) -> List[str]:
    """Split the data string using the provided regex for delimiters.

    :param str data: input string
    :param str delimsRe: regex for delimiters
    :return List[str]: items found between the delimiters
    """
    d = re.split(delimsRe, data)
    return [x for x in d if x]