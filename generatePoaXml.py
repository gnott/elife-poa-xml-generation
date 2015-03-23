import xml
from xml.dom.minidom import Document
from collections import namedtuple
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.etree import ElementTree
from xml.dom import minidom
import time
import re
from git import *
import settings

"""
create classes to represent affiliations, authors and papers.
pass the compount object to a class that writes the XML in the expected format.

## GOTCHAS/TODOs

self.orcid.set("xlink:href", contributor.orcid) returns an error

in aff, determine why some elements take an enclosing addr-line, and others don't 

in aff, if email is associated with aff, how do we deal with two atuhors from the same place,
but with different emails?

Think about moving the function that adds the doctype out of the funciton that 
does pretty printing. 
"""

class eLife2XML(object):

    def __init__(self, poa_article):
        """
        set the root node
        get the article type from the object passed in to the class
        set default values for items that are boilder plate for this XML 
        """
        self.root = Element('article')

        # set the boiler plate values
        self.journal_id_types = ["nlm-ta", "hwp", "publisher-id"]
        self.contrib_types = ["author", "editor"]
        self.date_types = ["received", "accepted"]
        self.elife_journal_id = "eLife"
        self.elife_journal_title = "eLife"
        self.elife_epub_issn = "2050-084X"
        self.elife_publisher_name = "eLife Sciences Publications, Ltd"

        self.root.set('article-type', poa_article.articleType)
        self.root.set('xmlns:mml', 'http://www.w3.org/1998/Math/MathML')
        self.root.set('xmlns:xlink', 'http://www.w3.org/1999/xlink')
        self.root.set('dtd-version', '1.1d1')

        # set comment
        generated = time.strftime("%Y-%m-%d %H:%M:%S")
        last_commit = get_last_commit_to_master()
        comment = Comment('generated by eLife at ' + generated + ' from version ' + last_commit)
        self.root.append(comment)

        # contributor conflict count, incremented when printing contrib xref
        self.conflict_count = 0
        if poa_article.conflict_default:
            # conf1 is reserved for the default conflict value, so increment now
            self.conflict_count += 1

        self.build(self.root, poa_article)

    def build(self, root, poa_article):
        self.set_frontmatter(self.root, poa_article)
        # self.set_title(self.root, poa_article)
        self.set_backmatter(self.root, poa_article)

    def set_frontmatter(self, parent, poa_article):
        self.front = SubElement(parent, 'front')
        self.set_journal_meta(self.front)
        self.set_article_meta(self.front, poa_article)        

    def set_backmatter(self, parent, poa_article):
        self.back = SubElement(parent, 'back')
        if poa_article.has_contributor_conflict() or poa_article.conflict_default:
            self.set_fn_group_competing_interest(self.back, poa_article)
        if len(poa_article.ethics) > 0:
            self.set_fn_group_ethics_information(self.back, poa_article)
     
    def set_fn_group_competing_interest(self, parent, poa_article):
        self.competing_interest = SubElement(parent, "fn-group")
        self.competing_interest.set("content-type", "competing-interest")
        title = SubElement(self.competing_interest, "title")
        title.text = "Competing interest"
        
        # Check if we are supplied a conflict default statement and set count accordingly
        if poa_article.conflict_default:
            conflict_count = 1
        else:
            conflict_count = 0
            
        for contributor in poa_article.contributors:
            if contributor.conflict:
                id = "conf" + str(conflict_count + 1)
                fn = SubElement(self.competing_interest, "fn")
                fn.set("fn-type", "conflict")
                fn.set("id", id)
                p = SubElement(fn, "p")
                p.text = contributor.given_name + " " + contributor.surname + ", "
                p.text = p.text + contributor.conflict + "."
                # increment
                conflict_count = conflict_count + 1
        if poa_article.conflict_default:
            # default for contributors with no conflicts
            if conflict_count > 1:
                # Change the default conflict text
                conflict_text = "The other authors declare that no competing interests exist."
            else:
                conflict_text = poa_article.conflict_default
            id = "conf1"
            fn = SubElement(self.competing_interest, "fn")
            fn.set("fn-type", "conflict")
            fn.set("id", id)
            p = SubElement(fn, "p")
            p.text = conflict_text
            conflict_count = conflict_count + 1

    def set_fn_group_ethics_information(self, parent, poa_article):
        self.competing_interest = SubElement(parent, "fn-group")
        self.competing_interest.set("content-type", "ethics-information")
        title = SubElement(self.competing_interest, "title")
        title.text = "Ethics"
        
        for ethic in poa_article.ethics:
            fn = SubElement(self.competing_interest, "fn")
            fn.set("fn-type", "other")
            p = SubElement(fn, "p")
            p.text = ethic

    def set_article_meta(self, parent, poa_article):
        self.article_meta = SubElement(parent, "article-meta")

        # article-id pub-id-type="publisher-id"
        if poa_article.manuscript:
            pub_id_type = "publisher-id"
            self.article_id = SubElement(self.article_meta, "article-id")
            self.article_id.text = str(int(poa_article.manuscript)).zfill(5)
            self.article_id.set("pub-id-type", pub_id_type)

        # article-id pub-id-type="doi"
        if poa_article.doi:
            pub_id_type = "doi"
            self.article_id = SubElement(self.article_meta, "article-id") 
            self.article_id.text = poa_article.doi
            self.article_id.set("pub-id-type", pub_id_type) 
        
        # article-categories
        self.set_article_categories(self.article_meta, poa_article)
        #
        self.set_title_group(self.article_meta, poa_article)
        
        #
        for contrib_type in self.contrib_types:
            self.set_contrib_group(self.article_meta, poa_article, contrib_type)
        #
        self.set_pub_date(self.article_meta, poa_article, "epub")
        #
        if poa_article.manuscript:
            self.elocation_id  = SubElement(self.article_meta, "elocation-id")
            self.elocation_id.text = "e" + str(int(poa_article.manuscript)).zfill(5)
        #
        if poa_article.dates:
            self.set_history(self.article_meta, poa_article)
        #
        if poa_article.license:
            self.set_permissions(self.article_meta, poa_article)
        #
        self.set_abstract(self.article_meta, poa_article)
        #
        if len(poa_article.author_keywords) > 0:
            self.set_kwd_group_author_keywords(self.article_meta, poa_article)
        #
        if len(poa_article.research_organisms) > 0:
            self.set_kwd_group_research_organism(self.article_meta, poa_article)

    def set_title_group(self, parent, poa_article):
        """
        Allows the addition of XML tags
        """
        root_tag_name = 'title-group'
        tag_name = 'article-title'
        root_xml_element = Element(root_tag_name)
        # Escape any unescaped ampersands
        title = xml_escape_ampersand(poa_article.title)
        
        # XML
        tagged_string = '<' + tag_name + '>' + title + '</' + tag_name + '>'
        reparsed = minidom.parseString(tagged_string)

        root_xml_element = append_minidom_xml_to_elementtree_xml(
            root_xml_element, reparsed
            )

        parent.append(root_xml_element)

    def set_journal_title_group(self, parent):
        """
        take boiler plate values from the init of the class 
        """
        
        # journal-title-group
        self.journal_title_group = SubElement(parent, "journal-title-group")

        # journal-title
        self.journal_title = SubElement(self.journal_title_group, "journal-title")
        self.journal_title.text = self.elife_journal_title 

    def set_journal_meta(self, parent):
        """
        take boiler plate values from the init of the class
        """
        self.journal_meta = SubElement(parent, "journal-meta")

        # journal-id
        for journal_id_type in self.journal_id_types:
            self.journal_id = SubElement(self.journal_meta, "journal-id")
            if journal_id_type == "nlm-ta":
                self.journal_id.text = self.elife_journal_id.lower()
            else:
                self.journal_id.text = self.elife_journal_id 
            self.journal_id.set("journal-id-type", journal_id_type) 

        #
        self.set_journal_title_group(self.journal_meta)

        # title-group
        self.issn = SubElement(self.journal_meta, "issn")
        self.issn.text = self.elife_epub_issn
        self.issn.set("publication-format", "electronic")

        # publisher
        self.publisher = SubElement(self.journal_meta, "publisher")
        self.publisher_name = SubElement(self.publisher, "publisher-name")
        self.publisher_name.text = self.elife_publisher_name

    def set_license(self, parent, poa_article):
        self.license = SubElement(parent, "license")

        self.license.set("xlink:href", poa_article.license.href)
        
        self.license_p = SubElement(self.license, "license-p")
        self.license_p.text = poa_article.license.p1
        
        ext_link = SubElement(self.license_p, "ext-link")
        ext_link.set("ext-link-type", "uri")
        ext_link.set("xlink:href", poa_article.license.href)
        ext_link.text = poa_article.license.name
        ext_link.tail = poa_article.license.p2

    def set_copyright(self, parent, poa_article):
        # Count authors (non-editors)
        non_editor = []
        for c in poa_article.contributors:
            if c.contrib_type != "editor":
                non_editor.append(c)
        
        if len(non_editor) > 2:
            contributor = non_editor[0]
            copyright_holder = contributor.surname + " et al"
        elif len(non_editor) == 2:
            contributor1 = non_editor[0]
            contributor2 = non_editor[1]
            copyright_holder = contributor1.surname + " & " + contributor2.surname
        elif len(non_editor) == 1:
            contributor = non_editor[0]
            copyright_holder = contributor.surname
        else:
            copyright_holder = ""
            
        # copyright-statement
        copyright_year = ""
        date = poa_article.get_date("license")
        if not date:
            # if no license date specified, use the article accepted date
            date = poa_article.get_date("accepted")
        if date:
            copyright_year = date.date.tm_year
            
        copyright_statement = u'\u00a9 ' + str(copyright_year) + ", " + copyright_holder
        self.copyright_statement = SubElement(parent, "copyright-statement")
        self.copyright_statement.text = copyright_statement
        
        # copyright-year
        self.copyright_year = SubElement(parent, "copyright-year")
        self.copyright_year.text = str(copyright_year)
        
        # copyright-holder
        self.copyright_holder = SubElement(parent, "copyright-holder")
        self.copyright_holder.text = copyright_holder
    
    def set_permissions(self, parent, poa_article):
        self.permissions = SubElement(parent, "permissions")
        if poa_article.license.copyright is True:
            self.set_copyright(self.permissions, poa_article)
        self.set_license(self.permissions, poa_article)

    def set_abstract(self, parent, poa_article):
        """
        Allows the addition of XML tags
        """
        root_tag_name = 'abstract'
        tag_name = 'p'
        root_xml_element = Element(root_tag_name)
        # Escape any unescaped ampersands
        abstract = xml_escape_ampersand(poa_article.abstract)
        
        # XML
        tagged_string = '<' + tag_name + '>' + abstract + '</' + tag_name + '>'
        reparsed = minidom.parseString(tagged_string)

        root_xml_element = append_minidom_xml_to_elementtree_xml(
            root_xml_element, reparsed
            )

        parent.append(root_xml_element)

    def set_contrib_group(self, parent, poa_article, contrib_type = None):
        # If contrib_type is None, all contributors will be added regardless of their type
        self.contrib_group = SubElement(parent, "contrib-group")
        if contrib_type == "editor":
            self.contrib_group.set("content-type", "section")

        for contributor in poa_article.contributors:
            if contrib_type:
                # Filter by contrib_type if supplied
                if contributor.contrib_type != contrib_type:
                    continue
                
            self.contrib = SubElement(self.contrib_group, "contrib")

            self.contrib.set("contrib-type", contributor.contrib_type)
            if contributor.corresp == True:
                self.contrib.set("corresp", "yes")
            if contributor.equal_contrib == True:
                self.contrib.set("equal_contrib", "yes")
            if contributor.auth_id:
                self.contrib.set("id", "author-" + str(contributor.auth_id))
                
            if contributor.collab:
                self.collab = SubElement(self.contrib, "collab")
                self.collab.text = contributor.collab
            else:
                self.name = SubElement(self.contrib, "name")
                self.surname = SubElement(self.name, "surname")
                self.surname.text = contributor.surname
                self.given_name = SubElement(self.name, "given-names")
                self.given_name.text = contributor.given_name

            if contrib_type == "editor":
                self.role = SubElement(self.contrib, "role")
                self.role.text = "Reviewing editor"

            if contributor.orcid:
                self.orcid = SubElement(self.contrib, "uri")
                self.orcid.set("content-type", "orcid")
                self.orcid.set("xlink:href", contributor.orcid)

            # Contributor conflict xref tag logic
            if contributor.conflict:
                rid = "conf" + str(self.conflict_count + 1)
                self.conflict_count += 1
            elif poa_article.conflict_default:
                rid = "conf1"
            else:
                rid = None

            for affiliation in contributor.affiliations:
                self.aff = SubElement(self.contrib, "aff")

                if contrib_type != "editor":
                    if affiliation.department:
                        self.department = SubElement(self.aff, "institution")
                        self.department.set("content-type", "dept")
                        self.department.text = affiliation.department
                        self.department.tail = ", "

                if affiliation.institution:
                    self.institution = SubElement(self.aff, "institution")
                    self.institution.text = affiliation.institution
                    self.institution.tail = ", "

                if affiliation.city:
                    self.addline = SubElement(self.aff, "addr-line")
                    self.city = SubElement(self.addline, "named-content")
                    self.city.set("content-type", "city")
                    self.city.text = affiliation.city
                    self.addline.tail = ", "

                if affiliation.country:
                    self.country = SubElement(self.aff, "country")
                    self.country.text = affiliation.country

                if affiliation.phone:
                    self.phone = SubElement(self.aff, "phone")
                    self.phone.text = affiliation.phone

                if affiliation.fax:
                    self.fax = SubElement(self.aff, "fax")
                    self.fax.text = affiliation.fax                    

                if affiliation.email:
                    self.email = SubElement(self.aff, "email")
                    self.email.text = affiliation.email

            # Contrib conflict xref
            if contrib_type != "editor":
                if rid:
                    self.xref = SubElement(self.contrib, "xref")
                    self.xref.set("ref-type", "fn")
                    self.xref.set("rid", rid)

    def set_article_categories(self, parent, poa_article):
        # article-categories
        if poa_article.get_display_channel() or len(poa_article.article_categories) > 0:
            self.article_categories = SubElement(parent, "article-categories")
            
            if poa_article.get_display_channel():
                # subj-group subj-group-type="display-channel"
                subj_group = SubElement(self.article_categories, "subj-group")
                subj_group.set("subj-group-type", "display-channel")
                subject = SubElement(subj_group, "subject")
                subject.text = poa_article.get_display_channel()
            
            for article_category in poa_article.article_categories:
                # subj-group subj-group-type="heading"
                subj_group = SubElement(self.article_categories, "subj-group")
                subj_group.set("subj-group-type", "heading")
                subject = SubElement(subj_group, "subject")
                subject.text = article_category

    def set_kwd_group_research_organism(self, parent, poa_article):
        # kwd-group kwd-group-type="research-organism"
        self.kwd_group = SubElement(parent, "kwd-group")
        self.kwd_group.set("kwd-group-type", "research-organism")
        title = SubElement(self.kwd_group, "title")
        title.text = "Research organism"
        for research_organism in poa_article.research_organisms:
            kwd = SubElement(self.kwd_group, "kwd")
            kwd.text = research_organism
            
    def set_kwd_group_author_keywords(self, parent, poa_article):
        # kwd-group kwd-group-type="author-keywords"
        self.kwd_group = SubElement(parent, "kwd-group")
        self.kwd_group.set("kwd-group-type", "author-keywords")
        title = SubElement(self.kwd_group, "title")
        title.text = "Author keywords"
        for author_keyword in poa_article.author_keywords:
            kwd = SubElement(self.kwd_group, "kwd")
            kwd.text = author_keyword

    def set_pub_date(self, parent, poa_article, pub_type):
        # pub-date pub-type = pub_type
        date = poa_article.get_date(pub_type)
        if date:
            self.pub_date = SubElement(parent, "pub-date")
            self.pub_date.set("pub-type", pub_type)
            year = SubElement(self.pub_date, "year")
            year.text = str(date.date.tm_year)

    def set_date(self, parent, poa_article, date_type):
        # date date-type = date_type
        date = poa_article.get_date(date_type)
        if date:
           self.date = SubElement(parent, "date")
           self.date.set("date-type", date_type)
           day = SubElement(self.date, "day")
           day.text = str(date.date.tm_mday).zfill(2)
           month = SubElement(self.date, "month")
           month.text = str(date.date.tm_mon).zfill(2)
           year = SubElement(self.date, "year")
           year.text = str(date.date.tm_year)

    def set_history(self, parent, poa_article):
        self.history = SubElement(parent, "history")
        
        for date_type in self.date_types:
            date = poa_article.get_date(date_type)
            if date:
                self.set_date(self.history, poa_article, date_type)

    def printXML(self):
        print self.root

    def prettyXML(self):
        publicId = '-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.1d1 20130915//EN'
        systemId = 'JATS-archivearticle1.dtd'
        encoding = 'utf-8'
        namespaceURI = None
        qualifiedName = "article"
    
        doctype = ElifeDocumentType(qualifiedName)
        doctype._identified_mixin_init(publicId, systemId)

        rough_string = ElementTree.tostring(self.root, encoding)
        reparsed = minidom.parseString(rough_string)
        if doctype:
            reparsed.insertBefore(doctype, reparsed.documentElement)
        #return reparsed.toprettyxml(indent="\t", encoding = encoding)
        # Switch to toxml() instead of toprettyxml() to solve extra whitespace issues
        return reparsed.toxml(encoding = encoding)

class ContributorAffiliation():
    phone = None
    fax = None
    email = None 

    department = None
    institution = None
    city = None 
    country = None

class eLifePOSContributor():
    """
    Currently we are not sure that we can get an auth_id for 
    all contributors, so this attribute remains an optional attribute. 
    """

    corresp = False
    equal_contrib = False

    auth_id = None
    orcid = None
    collab = None
    conflict = None
    group_author_key = None

    def __init__(self, contrib_type, surname, given_name, collab = None):
        self.contrib_type = contrib_type
        self.surname = surname
        self.given_name = given_name
        self.affiliations = []
        self.collab = collab

    def set_affiliation(self, affiliation):
        self.affiliations.append(affiliation)
        
    def set_conflict(self, conflict):
        self.conflict = conflict

class eLifeDate():
    """
    A struct_time date and a date_type
    """
    
    def __init__(self, date_type, date):
        self.date_type = date_type
        # Date as a time.struct_time
        self.date = date



class eLifeLicense():
    """
    License with some eLife preset values by license_id
    """
    
    license_id = None
    license_type = None
    copyright = False
    href = None
    name = None
    p1 = None
    p2 = None
    
    def __init__(self, license_id = None):
        if license_id:
            self.init_by_license_id(license_id)
        
    def init_by_license_id(self, license_id):
        """
        For license_id value, set the license properties
        """
        if int(license_id) == 1:
            self.license_id = license_id
            self.license_type = "open-access"
            self.copyright = True
            self.href = "http://creativecommons.org/licenses/by/4.0/"
            self.name = "Creative Commons Attribution License"
            self.p1 = "This article is distributed under the terms of the "
            self.p2 = " permitting unrestricted use and redistribution provided that the original author and source are credited."
        elif int(license_id) == 2:
            self.license_id = license_id
            self.license_type = "open-access"
            self.copyright = False
            self.href = "http://creativecommons.org/publicdomain/zero/1.0/"
            self.name = "Creative Commons CC0"
            self.p1 = "This is an open-access article, free of all copyright, and may be freely reproduced, distributed, transmitted, modified, built upon, or otherwise used by anyone for any lawful purpose. The work is made available under the "
            self.p2 = " public domain dedication."

class eLifeFundingAward():
    """
    An award group as part of a funding group
    """
    def __init__(self):
        self.award_ids = []
        self.institution_name = None
        self.institution_id = None

    def add_award_id(self, award_id):
        self.award_ids.append(award_id)

    def get_funder_identifier(self):
        # Funder identifier is the unique id found in the institution_id DOI
        try:
            return self.institution_id.split('/')[-1]
        except:
            return None

    def get_funder_name(self):
        # Alias for institution_name parsed from the XML
        return self.institution_name
        
    def get_award_number(self):
        # Alias for award_id parsed from the XML
        return self.award_id

class eLifeRef():
    """
    A ref or citation in the article to support crossref VOR deposits initially
    """
    def __init__(self):
        self.publication_type = None
        self.authors = []
        # For journals
        self.article_title = None
        self.source = None
        self.volume = None
        self.fpage = None
        self.lpage = None
        self.doi = None
        self.year = None
        # For books
        self.volume_title = None

    def add_author(self, author):
        # Author is a dict of values
        self.authors.append(author)
        
    def get_journal_title(self):
        # Alias for source
        return self.source

class eLifePOA():
    """
    We include some boiler plate in the init, namely articleType
    """
    contributors = [] 

    def __init__(self, doi, title):
        self.articleType = "research-article"
        self.display_channel = None
        self.doi = doi 
        self.contributors = [] 
        self.title = title 
        self.abstract = ""
        self.research_organisms = []
        self.manuscript = None
        self.dates = None
        self.license = None
        self.article_categories = []
        self.conflict_default = None
        self.ethics = []
        self.author_keywords = []
        self.funding_awards = []
        self.ref_list = []
        # For PubMed function a hook to specify if article was ever through PoA pipeline
        self.was_ever_poa = None
        self.is_poa = None
        self.volume = None

    def add_contributor(self, contributor):
        self.contributors.append(contributor)

    def add_research_organism(self, research_organism):
        self.research_organisms.append(research_organism)

    def add_date(self, date):
        if not self.dates:
            self.dates = {}
        self.dates[date.date_type] = date
        
    def get_date(self, date_type):
        try:
            return self.dates[date_type]
        except (KeyError, TypeError):
            return None
        
    def get_display_channel(self):
        # display-channel string partly relates to the articleType
        return self.display_channel
    
    def add_article_category(self, article_category):
        self.article_categories.append(article_category)
        
    def has_contributor_conflict(self):
        # Return True if any contributors have a conflict
        for contributor in self.contributors:
            if contributor.conflict:
                return True
        return False
    
    def add_ethic(self, ethic):
        self.ethics.append(ethic)
        
    def add_author_keyword(self, author_keyword):
        self.author_keywords.append(author_keyword)


class ElifeDocumentType(minidom.DocumentType):
    """
    Override minidom.DocumentType in order to get
    double quotes in the DOCTYPE rather than single quotes
    """
    def writexml(self, writer, indent="", addindent="", newl=""):
        writer.write("<!DOCTYPE ")
        writer.write(self.name)
        if self.publicId:
            writer.write('%s  PUBLIC "%s"%s  "%s"'
                         % (newl, self.publicId, newl, self.systemId))
        elif self.systemId:
            writer.write('%s  SYSTEM "%s"' % (newl, self.systemId))
        if self.internalSubset is not None:
            writer.write(" [")
            writer.write(self.internalSubset)
            writer.write("]")
        writer.write(">"+newl)

def repl(m):
    # Convert hex to int to unicode character
    chr_code = int(m.group(1), 16)
    return unichr(chr_code)

def get_last_commit_to_master():
    """
    returns the last commit on the master branch. It would be more ideal to get the commit 
    from the branch we are currently on, but as this is a check mostly to help
    with production issues, returning the commit from master will be sufficient. 
    """
    repo = Repo(".")
    last_commit = None
    try:
        last_commit = repo.commits()[0] 
    except AttributeError:
        # Optimised for version 0.3.2.RC1
        last_commit = repo.head.commit
    return str(last_commit) 
    # commit =  repo.heads[0].commit 
    # return str(commit) 

def entity_to_unicode(s):
    """
    Quick convert unicode HTML entities to unicode characters
    using a regular expression replacement
    """
    s = re.sub(r"&#x(....);", repl, s)
    return s

def xml_escape_ampersand(s):
    """
    Quick convert unicode ampersand characters not associated with
    a numbered entity to a plain &amp;
    """

    # The pattern below is match & that is not immediately followed by #
    s = re.sub(r"&(?!\#)", '&amp;', s)
    return s

def decode_brackets(s):
    """
    Decode angle bracket escape sequence
    used to encode XML content
    """
    s = s.replace(settings.LESS_THAN_ESCAPE_SEQUENCE, '<')
    s = s.replace(settings.GREATER_THAN_ESCAPE_SEQUENCE, '>')
    return s

def replace_tags(s, from_tag = 'i', to_tag = 'italic'):
    """
    Replace tags such as <i> to <italic>
    <sup> and <sub> are allowed and do not need to be replaced
    This does not validate markup
    """
    s = s.replace('<' + from_tag + '>', '<' + to_tag + '>')
    s = s.replace('</' + from_tag + '>', '</' + to_tag + '>')
    return s

def escape_unmatched_angle_brackets(s):
    """
    In order to make an XML string less malformed, escape
    unmatched less than tags that are not part of an allowed tag
    Note: Very, very basic, and do not try regex \1 style replacements
      on unicode ever again! Instead this uses string replace
    """
    allowed_tags = ['<i>','</i>',
                    '<italic>','</italic>',
                    '<sup>','</sup>',
                    '<sub>','</sub>']
    
    # Split string on tags
    tags = re.split('(<.*?>)', s)
    #print tags

    for i in range(len(tags)):
        val = tags[i]
        
        # Use angle bracket character counts to find unmatched tags
        #  as well as our allowed_tags list to ignore good tags
        
        if val.count('<') == val.count('>') and val not in allowed_tags:
            val = val.replace('<', '&lt;')
            val = val.replace('>', '&gt;')
        else:
            # Count how many unmatched tags we have
            while val.count('<') != val.count('>'):
                if val.count('<') != val.count('>') and val.count('<') > 0:
                    val = val.replace('<', '&lt;', 1)
                elif val.count('<') != val.count('>') and val.count('>') > 0:
                    val = val.replace('>', '&gt;', 1)
        tags[i] = val

    return ''.join(tags)
    
def convert_to_xml_string(s):
    """
    For input strings with escaped tags and special characters
    issue a set of conversion functions to prepare it prior
    to adding it to an article object
    """
    s = entity_to_unicode(s).encode('utf-8')
    s = decode_brackets(s)
    s = replace_tags(s)
    s = escape_unmatched_angle_brackets(s)
    return s

def append_minidom_xml_to_elementtree_xml(parent, xml, recursive = False):
    """
    Recursively,
    Given an ElementTree.Element as parent, and a minidom instance as xml,
    append the tags and content from xml to parent
    Used primarily for adding a snippet of XML with <italic> tags
    """

    # Get the root tag name
    if recursive is False:
        tag_name = xml.documentElement.tagName
        node = xml.getElementsByTagName(tag_name)[0]
        new_elem = SubElement(parent, tag_name)
    else:
        node = xml
        tag_name = node.tagName
        new_elem = parent

    i = 0
    for child_node in node.childNodes:
        if child_node.nodeName == '#text':
            if not new_elem.text and i <= 0:
                new_elem.text = child_node.nodeValue
            elif not new_elem.text and i > 0:
                new_elem_sub.tail = child_node.nodeValue
            else:
                new_elem_sub.tail = child_node.nodeValue
                
        elif child_node.childNodes is not None:
            new_elem_sub = SubElement(new_elem, child_node.tagName)
            new_elem_sub = append_minidom_xml_to_elementtree_xml(new_elem_sub, child_node, True)

        i = i + 1

    # Debug
    #encoding = 'utf-8'
    #rough_string = ElementTree.tostring(parent, encoding)
    #print rough_string
    
    return parent
    

if __name__ == '__main__':

    # test affiliations 
    aff1 = ContributorAffiliation()
    aff1.department = entity_to_unicode("Edit&#x00F3;ri&#x00E1;l&#x2212;Dep&#x00E1;rtment")
    aff1.institution = "eLife"
    aff1.city = "Cambridge"
    aff1.country = "UK"
    aff1.email = "m.harrsion@elifesciecnes.org"

    aff2 = ContributorAffiliation()
    aff2.department = entity_to_unicode("Coffe Ho&#x00FC;se")
    aff2.institution = "hipster"
    aff2.city = "London"
    aff2.country = "UK"
    aff2.email = "m.harrsion@elifesciecnes.org"

    aff3 = ContributorAffiliation()
    aff3.department = entity_to_unicode("Coffe Ho&#x00FC;se")
    aff3.institution = "hipster"
    aff3.city = "London"
    aff3.country = "UK"
    aff3.email = "i.mulvany@elifesciences.org"


    # test authors 
    auth1 = eLifePOSContributor("author", "Harrison", "Melissa")
    auth1.auth_id = "029323as"
    auth1.corresp = True
    auth1.orcid = "this is an orcid"
    auth1.set_affiliation(aff1)
    auth1.set_affiliation(aff2)
    auth1.set_conflict("eLife staff")

    auth2 = eLifePOSContributor("author", "Mulvany", "Ian")
    auth2.auth_id = "ANOTHER_ID_2"
    auth2.corresp = True
    auth2.set_affiliation(aff3)
    
    # test editor
    ed1 = eLifePOSContributor("editor", "Harrison", "Melissa")
    ed1.auth_id = "029323as"
    ed1.set_affiliation(aff1)

    # group collab author
    auth3 = eLifePOSContributor("author", None, None, "eLife author group")
    auth3.auth_id = "groupAu1"

    # dates
    t = time.strptime("2013-10-03", "%Y-%m-%d")
    date_epub = eLifeDate("epub", t)
    date_accepted = eLifeDate("accepted", t)
    date_received = eLifeDate("received", t)
    # copyright date as the license date
    t_license = time.strptime("2013-10-03", "%Y-%m-%d")
    date_license = eLifeDate("license", t_license)
    license = eLifeLicense(1)

    # test article 
    doi = "10.7554/eLife.00929"
    manuscript = 929
    title = "The Test Title"
    abstract = "Test abstract"
    display_channel = "Research article"
    newArticle = eLifePOA(doi, title)
    newArticle.abstract = abstract
    newArticle.display_channel = display_channel
    newArticle.conflict_default = "The authors declare that no competing interests exist."
    
    newArticle.add_ethic("Human subjects: The eLife IRB approved our study")
    newArticle.add_ethic("Animal experimentation: This study was performed in strict accordance with the recommendations in the Guide for the Care and Use of Laboratory Animals of the National Institutes of Health. All of the animals were handled according to approved institutional animal care and use committee (IACUC) protocols (#08-133) of the University of Arizona. The protocol was approved by the Committee on the Ethics of Animal Experiments of the University of Minnesota (Permit Number: 27-2956).")

    newArticle.manuscript = manuscript
    newArticle.add_research_organism("E. coli")
    newArticle.add_research_organism("Mouse")

    newArticle.add_contributor(auth1)
    newArticle.add_contributor(auth2)
    newArticle.add_contributor(auth3)
    newArticle.add_contributor(ed1)
    
    newArticle.add_date(date_epub)
    newArticle.add_date(date_accepted)
    newArticle.add_date(date_received)
    newArticle.add_date(date_license)
    
    newArticle.license = license
    
    newArticle.add_article_category("Cell biology")

    # test the XML generator 
    eXML = eLife2XML(newArticle)
    prettyXML = eXML.prettyXML()
    print prettyXML




