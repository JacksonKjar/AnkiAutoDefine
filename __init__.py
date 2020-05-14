from aqt import mw, editor
from aqt.qt import QDialog, QGridLayout, QPushButton, QLabel
from anki.hooks import addHook, remHook, runHook

from functools import partial
import re

from . import definitionGetter

# stores the entries that need to be added when dialogs end
finalEntries = []
first = True
config = mw.addonManager.getConfig(__name__)

# adds the selected dictionary entry and closes dialog
def buttonPressed(entry,window):
    global finalEntries
    finalEntries.append(entry)
    window.close()

def getBoldWords(html):
    return re.findall(r'<b>(.+?)</b>',html)

def theMagic(flag, n, fidx):
    global finalEntries, first, config
    fields = mw.col.models.fieldNames(n.model())
    for notetype in config["notetypes"]:
        if n.model()['name'] == notetype["name"]:
            if fields[fidx] == notetype["src"]:
                src = fields[fidx]
                dst = notetype["dst"]
                try:
                    n[dst] == n[src]
                except:
                    raise ValueError("The dst and src fields in config don't match those on the card")
                # conditions to confirm functionality should be run
                if n[dst] == "" and n[src] != "":
                    aw = None
                    for widget in mw.app.allWidgets():
                        # finds the editor in use
                        if isinstance(widget, editor.EditorWebView) and widget.editor.note is n:
                            aw = widget
                            break
                    if aw != None:
                        # because this add-on loads first and it reacts with the reading generator strangely, gotta put it in the back
                        if first:
                            first = False
                            remHook('editFocusLost', theMagic)
                            runHook('editFocusLost',flag,n,fidx)
                            addHook('editFocusLost', theMagic)
                        boldWords = getBoldWords(n[src])
                        # runs the dialogs
                        for word in boldWords:
                            entries = definitionGetter.parseSearch(word)
                            if(len(entries) < 2):
                                finalEntries.append(entries[0])
                                continue
                            d = QDialog(aw)
                            grid = QGridLayout()

                            # adds found definitions to dialog window
                            for x in range(len(entries)):
                                button = QPushButton(entries[x].word)
                                button.clicked.connect(partial(buttonPressed, entries[x],d))
                                label = QLabel()
                                label.setText(entries[x].shortDef)
                                label.setWordWrap(True)
                                grid.addWidget(button,x,0)
                                grid.addWidget(label,x,1,1,5)
                            d.setLayout(grid)
                            d.exec_()

                        # puts the output into the note and saves
                        output = ""
                        for entry in finalEntries:
                            output += "<div><b>"+entry.word+":</b> " + entry.getFullDef() + "</div>"
                        n[dst] = output
                        n.flush()
                        aw.editor.loadNote(focusTo=fidx+1)
                        finalEntries = []

                        # prevents focus from advancing and messing the edits up
                        return False
            break
    return flag

# tells anki to call theMagic when focus is lost (you move out of a text field or something)
addHook('editFocusLost', theMagic)
