import xml.etree.ElementTree as ET


def xml2dict(s):
    root = ET.fromstring(s)
    result = {root.tag: parse(root)}
    return result


def parse(ele):
    result = None
    tags = []
    p_childs = []
    for child in ele.getchildren():
        tags.append(child.tag)
        p_childs.append((child.tag, parse(child)))

    if not tags:
        text = ele.text
        if text is not None:
            text = text.strip()
        else:
            text = ''
        return text

    if len(set(tags)) < len(tags):
        result = []
        result = [dict([x]) for x in p_childs]
    else:
        result = {}
        result = dict(p_childs)
    return result
