import requests
import re
from functools import partial

# stores the entries that need to be added when dialogs end
finalEntries = []
first = True

# dictionary entry object to organize the word and definitions.
class dictionaryEntry:

    @classmethod
    def fromSearchPage(cls, name, dataHTML):
        shortDef = re.search(r'<p class="text">(.+?)</p>',dataHTML).group(1)
        url = "https://dictionary.goo.ne.jp"+re.search(r'(/word/.+?)"',dataHTML).group(1)
        word = re.search(r'<p class="title">(.+?) ',dataHTML).group(1)
        return cls(name, word, shortDef, url)

    @classmethod
    def fromEntryPage(cls, name, dataHTML):
        word = re.search(r'"og:title" content="(.+?)の意味',dataHTML,re.DOTALL).group(1)
        reg = re.compile('<div id="jn-.+?_".+?<div class="content-box contents_area meaning_area p10">(.+?)<!-- /contents -->',re.DOTALL)
        shortDef = cleanDefinition(re.search(reg,dataHTML).group(1))
        return cls(name, word, shortDef, "")

    def __init__(self, name, word, shortDef, url):
        self.name = name
        self.shortDef = re.sub(r'<img.+?>|&#x32..;',"",shortDef)
        self.url = url
        self.word = word
    
    @classmethod
    def failedSearchEntry(cls, word):
        return cls("失敗","失敗","goo辞書で「" + word + "」に一致する情報は見つかりませんでした","")

    @classmethod
    def connectionErrorEntry(cls):
        return cls("失敗","失敗","goo辞書に接続出来ませんでした","")

    # returns an expanded version of the definition
    def getFullDef(self):
        if self.url == "" or self.shortDef[-3:] != "...":
            return self.shortDef
        else:
            try:
                idNum = self.url.split('#')[-1]
                entryPage = requests.get(self.url).text
                reg = re.compile('<div id="' + idNum + '_".+?<div class="content-box contents_area meaning_area p10">(.+?)<!-- /contents -->',re.DOTALL)
                return cleanDefinition(re.search(reg,entryPage).group(1))
            except requests.exceptions.ConnectionError:
                return self.shortDef

    def __str__(self):
        return self.word+ ": " + self.shortDef

def cleanDefinition(dirty):
    dirtyLines = re.findall(r'<p class="text">.+?</p>|<div class="text">.+?</div>',dirty,re.DOTALL)
    answer = ""
    for line in dirtyLines:
        answer += re.sub(r'<.*?>|&thinsp;|&#x32..;',"",line) + "\n"
    return answer

# adds the selected dictionary entry and closes dialog
def buttonPressed(entry,window):
    global finalEntries
    finalEntries.append(entry)
    window.close()

def getBoldWords(html):
    return re.findall(r'<b>(.+?)</b>',html)
    
# searches for the passed word, returning the html of the page
def getSearchPage(word):
    searchPage = requests.get(urlEncode(word)).text
    if "一致する情報は見つかりませんでした" in searchPage:
        raise ValueError("goo辞書で一致する情報は見つかりませんでした")
    return searchPage

# Returns an array containing dictionaryEntry objects corresponding to the word passed as a parameter
def parseSearch(word): 
    try:
        searchPage = getSearchPage(word)
    except ValueError:
        return [dictionaryEntry.failedSearchEntry(word)]
    except requests.exceptions.ConnectionError:
        return [dictionaryEntry.connectionErrorEntry()]

    try:
        resultsString = re.search(r'<ul class="content_list idiom lsize">(.+?)</div>', searchPage, re.DOTALL).group(1)
    except AttributeError:
        return [dictionaryEntry.fromEntryPage(word, searchPage)]

    entries = []
    for result in re.findall(r'<a href=.+?</a>', resultsString,re.DOTALL):
        entries.append(dictionaryEntry.fromSearchPage(word, result))
    return entries

# Returns the encoding of the word as used in goo辞書's url
def urlEncode(word):
    codedWord = str(word.encode('utf-8'))[2:-1].upper()
    finalized = ""
    for i in range(2, len(codedWord)-1 ,4):
        finalized = finalized + "%" + codedWord[i:i+2]
    return "https://dictionary.goo.ne.jp/srch/jn/" + finalized + "/m1u/"

for word in parseSearch("制御"):
    print(word)
