from lxml import etree

def get_file_content(filename):
    f = open(filename, "r")
    content = f.read()
    f.close
    return content

good_file = "demo/elife_poa_e00003.xml"
bad_file  = "demo/elife_poa_e00003_bad.xml"
#filename = "generated_xml_output/elife_poa_e00003_bad.xml"
dtd_filename = "dtd/archivearticle3/archivearticle3.dtd"

dtd = etree.DTD(dtd_filename)

content = get_file_content(good_file)
root = etree.XML(content)
print(dtd.validate(root))
# True

content = get_file_content(bad_file)
root = etree.XML(content)
print(dtd.validate(root))
# False
print(dtd.error_log.filter_from_errors())