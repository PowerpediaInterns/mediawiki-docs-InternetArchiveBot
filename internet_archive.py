"""
Bot Goal:
 Check for validity of a string encounted traversing wiki.
 This is done by making a request on each link external to the wiki.
 If a request is bad then that link is tagged as a bad link.
"""

import json
import re
import requests
import urllib3
import pywikibot

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REV_PAGE = "Powerpedia:internet_archive_REV"
CATEGORY = "bad_links"
PAGES_LIMIT = 1
REQUEST_TIMEOUT = 5.0

#Global list of all links
links_table = {}

def get_api_url() -> str:
    """
    Retrieves the API URL of the wiki

    :return: String of the path to the API URL of the wiki
    """

    site = pywikibot.Site()
    url = site.protocol() + "://" + site.hostname() + site.apipath()
    return url
def check_last_page() -> str:
    """
    Checks to see if REV_PAGE has any useful last page to start the script from
    If it does return that page as the last_page, and if not return an empty string.
    Need to query the wiki for page rev information.
    Using this: https://www.mediawiki.org/wiki/API:Revisions

    :param: none
    :return: page last modified. Stored at REV_PAGE on wiki.  returns empty string if
    no information is available at that page.
    """

    page = pywikibot.Page(pywikibot.Site(), title=REV_PAGE)

    #Check to make sure the revision page exists.  If it doesn't create a new empty page and return
    #an empty string.
    if not page.exists():
        print("Revision page \""+ REV_PAGE +"\" not found...  Adding")
        page.text = ""
        page.save()
        return ""

    if not page.get():
        print("No valid revision on this page found\n")
        return ""


    #Need to replace ' with " so json.loads() can properly change it from a string to a dict.
    page_text = page.get().replace('\'', '\"')
    page_contents = json.loads(page_text)

    if page_contents['title']:
        return page_contents['title']

    print("No valid revision page found\n")
    return ""

def get_revisions(page_title: str) -> list:
    """
    Gets the revision information from a page specifed by its page title.

    :param page_title: string of the page title to get the revisions of
    :return: list containing user, time, and title of last revision on
    this page.
    """

    session = requests.Session()
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": page_title,
        "rvprop": "timestamp|user",
        "rvslots": "main",
        "formatversion": "2",
        "format": "json"
    }

    request = session.get(url=get_api_url(), params=params, verify=False)
    data = request.json()

    #Need to make sure key values 'query' and 'pages' are in the data dict.
    if not ('query' in data and 'pages' in data['query']):
        print("No valid page found...")
        return ""

    page = data['query']['pages'][0]

    #Checking for 'missing' or no 'revisions' if so that means nothing of value
    #is page and should just return ""
    if 'missing' in page or not 'revisions' in page:
        print("No revision information found for page " + page_title + "\n")
        return ""
    rev_info = page['revisions'][0]

    return {"user": rev_info['user'],
            "time": rev_info['timestamp'],
            "title": page_title}

def update_last_page(current_page: str) -> None:
    """
    Sets the page text of REV_PAGE to the latest revision information from current_page

    :param: current_page title of page to set revision information of
    :return: none
    """
    rev = get_revisions(current_page)
    page = pywikibot.Page(pywikibot.Site(), title=REV_PAGE)
    page.text = rev
    page.save()


def get_params(continue_from="") -> {}:
    """
    Gets the parameters dictionary to make the GET request to the wiki

    :param continue_from: String of page title to continue from; defaults to beginning of wiki
    :return: a dictionary of the parameters
    """

    return {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "apcontinue": continue_from,
        "aplimit": PAGES_LIMIT
    }






def check_link(link: str) -> bool:
    """
    Checks the validity of a link by making a request & seeing if it fails.
    """
    session = requests.Session()
    print("Checking link: "+ link)
    try:
        request = session.get(url=link, timeout=REQUEST_TIMEOUT)
        return request.status_code == 200
    except Exception:
        return False

def check_links(page_id: str, url: str, page_title: str) -> None:
    """
    Iterates through a page and checks links on that page.
    """

    PARAMS = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "extlinks"
    }
    session = requests.Session()
    request = session.get(url=url, params=PARAMS, verify=False)
    page = request.json()

    if not ("query" in page
             and "pages" in page["query"]
             and str(page_id) in page["query"]["pages"]
             and "extlinks" in page["query"]["pages"][str(page_id)]):
        print("Page " + page_title + " doesn't contain extlinks... Continuing")

        return

    links = page["query"]["pages"][str(page_id)]["extlinks"]

    #Local list of links.  This is needed so we don't have to recheck links
    #for each page.  Instead we keep 2 identical records.
    page_links = {}

    for link in links:

        #Make sure we only check each link once
        if link["*"] in links_table:
            continue

        link_status = not check_link(link["*"])
        #Link not found in link table.  Therefore we need to check it
        if link_status:
            print("Invalid link: \""+ link["*"] + "\" found. ")
            links_table[link["*"]] = False
            #Link has been checked good add it to the table as good
        elif not link_status:
            links_table[link["*"]] = True

    #Copy the links found in this page to page_links
    for link in links:
        page_links[link["*"]] = links_table[link["*"]]

    update_page(page_title, page_links)


    #[[Category:Pages with Broken External Link]]
def update_page(page_title: str, links: dict) -> None:
    """
    Updates a page a with a given page title
    """
    page = pywikibot.Page(pywikibot.Site(), title=page_title)

    if not page.exists():
        print("Page \"" + title + "\" Not found.  Exiting")
        return
    page_text =  page.text
    bad_link_found = False
    for link in links:
        if not links[link]:
            re_sub = r"\[{2}\s*" + link.replace('.', '\.') + r".*\]{2}"
            page_text = re.sub(re_sub,
                               "{{Bad Link |link_string="+ link +" }}",
                               page_text)
            bad_link_found = True
        elif links[link]:
            re_sub = r"\{{2}\s*Bad\s+Link\s+\|link_string=\s*"+ link.replace('.', '\.') +r"\s*\}{2}"
            page_text = re.sub(re_sub, "[[" + link + "]]", page_text)


    #Case 0, First bad link found on page.  Category addition needed
    if bad_link_found and not re.search(r"\[{2}\s*Category\s*:\s*bad_links\s*]{2}",
              page_text):
        page_text = page_text + "\n [[Category:"+ CATEGORY +"]]"
        page.text = page_text
        page.save(u"Bad links found", botflag=True)

    #Case 1, there are no bad links and category bad_links needs to be removed.
    elif not bad_link_found and re.search(r"\[{2}\s*Category\s*:\s*bad_links\s*]{2}",
              page_text):
        page_text = re.sub(r"\[{2}\s*Category\s*:\s*bad_links\s*]{2}",
               "",
               page_text)
        page.text = page_text
        page.save("Category Bad Links removed", botflag=True)

    #Case 2, Category is fine, and page just needs to be saved.
    else:
        page.text = page_text
        page.save("Bad links found", botflag=True)



def modify_pages(url: str, last_title: str) -> None:
    """
    Retrieves a Page Generator with all old pages to be tagged

    :param url: String of the path to the API URL of the wiki
    :param last_title: String of the last title scanned
    :return: None
    """

    # Retrieving the JSON and extracting page titles
    session = requests.Session()
    request = session.get(url=url, params=get_params(last_title), verify=False)
    pages_json = request.json()

    if not ("query" in pages_json and "allpages" in pages_json["query"]):
        print("query error...  Exiting")
        return

    last_title = ""
    pages = pages_json["query"]["allpages"]
    for page in pages:
        print("Checking Page " + str(page))
        check_links(page_id=page["pageid"],
                    url=url,
                    page_title=page["title"])
        last_title = page["title"]


    if "continue" in pages_json:
        continue_from_title = last_title
        print("\nContinuing from:", continue_from_title, "next run.")
    else:
        continue_from_title = ""

    update_last_page(continue_from_title)


def main() -> None:
    """
    Driver. Iterates through the wiki and adds TEMPLATE where needed.
    """
    # Retrieving the wiki URL
    url = get_api_url()
    last_title = check_last_page()

    if last_title:
        print("last page found")
    else:
        print("No last page found")

    modify_pages(url, last_title)


    print("\nNo pages left to be tagged")


if __name__ == '__main__':
    main()
