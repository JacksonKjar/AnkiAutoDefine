from functools import partial
import re

import anki
from aqt import mw, editor, gui_hooks
from aqt.qt import QDialog, QGridLayout, QPushButton, QLabel

from . import definitionGetter

# stores the entries that need to be added when dialogs end
finalEntries = []
config = mw.addonManager.getConfig(__name__)

# adds the selected dictionary entry and closes dialog
def buttonPressed(entry,window):
    global finalEntries
    finalEntries.append(entry)
    window.close()

def getBoldWords(html):
    return re.findall(r'<b>(.+?)</b>',html)

def getNoteType(name):
    global config
    for notetype in config['notetypes']:
        if(name == notetype['name']): 
            return notetype
    return None

def getActiveWindow(note):
    for widget in mw.app.allWidgets():
        # finds the editor in use
        if isinstance(widget, editor.EditorWebView) and widget.editor.note is note:
            return widget
    return None

def getDefinitionChoiceDialog(aw, entries):
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
    return d

def theMagic(changed: bool, note: anki.notes.Note, current_field_idx: int):
    global finalEntries, config
    fields = mw.col.models.field_names(note.note_type())
    notetype = getNoteType(note.note_type()['name'])
    if not notetype:
        # not a notetype that has the add-on enabled, don't do anything
        return changed

    if fields[current_field_idx] != notetype["src"]:
        # not the src field that has been edited, don't do anything
        return changed
    src = fields[current_field_idx]
    dst = notetype["dst"]

    if not dst:
        raise ValueError("The dst and src fields in config don't match those on the card")
    
    if note[dst]:
        # dst isn't empty, to avoid overwriting data, don't do anything
        return changed

    aw = getActiveWindow(note)
    if not aw:
        return changed
    
    boldWords = getBoldWords(note[src])
    # runs the dialogs
    for word in boldWords:
        entries = definitionGetter.parseSearch(word)
        if(len(entries) == 1):
            finalEntries.append(entries[0])
        else:
            getDefinitionChoiceDialog(aw, entries).exec_()

    # puts the output into the note and saves
    output = ""
    for entry in finalEntries:
        output += "<div><b>"+entry.word+":</b> " + entry.getFullDef() + "</div>"
    note[dst] = output
    try:
        note._to_backend_note()
    except AttributeError:
        note.flush()
    aw.editor.loadNote(focusTo=current_field_idx+1)
    finalEntries = []

    # prevents focus from advancing and messing the edits up
    return False

# tells anki to call theMagic when focus is lost (you move out of a text field or something)
gui_hooks.editor_did_unfocus_field.append(theMagic)
