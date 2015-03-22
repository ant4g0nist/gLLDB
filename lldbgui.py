#!/usr/bin/env python

#global
ARCH_MAP={
    ('<', '64-bit'): 'x86_64',
    ('<', '32-bit'): 'i386',
    ('>', '64-bit'): 'ppc64',
    ('>', '32-bit'): 'ppc',
}
target=""

#imports
import os
import sys
import time
import glob
import string
import random
import commands

import subprocess

import platform
from macholib.MachO import MachO
from macholib.mach_o import *


from Cocoa import *
from Foundation import NSObject
from Foundation import *
from AppKit import *
from AppKit import NSStatusBar, NSStatusItem, NSVariableStatusItemLength



try:
    import lldb
except ImportError:
    lldb_python_dirs = list()
    platform_system = platform.system()
    if platform_system == 'Darwin':
        xcode_dir = commands.getoutput("xcode-select --print-path")
        if xcode_dir:
            lldb_python_dirs.append(os.path.realpath(xcode_dir + '/../SharedFrameworks/LLDB.framework/Resources/Python'))
            lldb_python_dirs.append(xcode_dir + '/Library/PrivateFrameworks/LLDB.framework/Resources/Python')
        lldb_python_dirs.append('/System/Library/PrivateFrameworks/LLDB.framework/Resources/Python')
    success = False
    for lldb_python_dir in lldb_python_dirs:
        if os.path.exists(lldb_python_dir):
            if not (sys.path.__contains__(lldb_python_dir)):
                sys.path.append(lldb_python_dir)
                try:
                    import lldb
                except ImportError:
                    pass
                else:
                    print 'imported lldb from: "%s"' % (lldb_python_dir)
                    success = True
                    break
    if not success:
        print "error: couldn't locate the 'lldb' module, please set PYTHONPATH correctly"
        sys.exit(1)
allFuncsNames=[]
funcnames=[]

def IsCodeType(symbol):
    """Check whether an SBSymbol represents code."""
    return symbol.GetType() == lldb.eSymbolTypeCode

def returnFuntions(target,file):
    global funcnames
    f=str(file).split('\n')[0]
    for i in target.modules:
        j=str(i.file)
        if f==j:
            for k in i.symbols:
                if IsCodeType(k) or not k.GetType()==24 and k.name!="_mh_execute_header" and k.name!="radr://5614542":
                    funcnames.append(k)
    return funcnames

#utitlity functions
def run_commands(command_interpreter, commands):
    return_obj = lldb.SBCommandReturnObject()
    for command in commands:
        print command
        command_interpreter.HandleCommand(command,return_obj)
        if return_obj.Succeeded():
            return return_obj.GetOutput()
        else:
            print return_obj.GetError()
            return False
class Alert(object):
    
    def __init__(self, messageText):
        super(Alert, self).__init__()
        self.messageText = messageText
        self.informativeText = ""
        self.buttons = []
    
    def displayAlert(self):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(self.messageText)
        alert.setInformativeText_(self.informativeText)
        alert.setAlertStyle_(NSInformationalAlertStyle)
        for button in self.buttons:
            alert.addButtonWithTitle_(button)
        NSApp.activateIgnoringOtherApps_(True)
        self.buttonPressed = alert.runModal()

def alert(message="Default Message", info_text="", buttons=["OK"]):    
    ap = Alert(message)
    ap.informativeText = info_text
    ap.buttons = buttons
    ap.displayAlert()
    return ap.buttonPressed

#Controller for xib
class Controller(NSWindowController):
    lldbout = objc.IBOutlet()
    lldbin = objc.IBOutlet()
    # logout = objc.IBOutlet()
    reg = objc.IBOutlet()
    nextIns = objc.IBOutlet()
    tv = objc.IBOutlet()
    disas = objc.IBOutlet()
    ds = NSMutableArray.alloc().init()

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)
        self.target()
    def _setup_status_bar(self):
        """
            Set up the status bar in the Mac menu
        """
        pass
    
    def awakeFromNib(self):
        """
            Set up the UI once the NIB is initialised
        """
        self._setup_status_bar()
        self.lldbin.setDelegate_(self)
        self.lldbout.setEditable_(False)
        self.reg.setEditable_(False)
        self.nextIns.setEditable_(False)
        self.disas.setEditable_(False)


    # @objc.IBAction
    def runcmd(self):
        cmd=str(self.lldbin.stringValue())
        out=run_commands(command_interpreter,[cmd])
                
        if out!=False:
            op=str(self.lldbout.string())+'\n'+'*'*10+'\n[+]\tCMD:\t{0}\n'.format(cmd)+out
            self.lldbout.setString_(op)
        else:
            err="[-]\tThere was an error please try again"
            op=str(self.lldbout.string())+'\n'+'*'*10+'\n[+]\tCMD:\t{0}\n'.format(cmd)+err
            self.lldbout.setString_(op)

        out=run_commands(command_interpreter,['register read'])
        if out:
            self.reg.setString_(out)
        out=run_commands(command_interpreter,['disassemble -p'])
        if out:
            self.nextIns.setString_(out)

    @objc.IBAction  
    def target_(self, sender):
        self.target()

    def target(self):
        filename=""
        global debugger
        global target
        global allFuncsNames

        panel = NSOpenPanel.openPanel()
        panel.setCanCreateDirectories_(True)
        panel.setCanChooseDirectories_(True)
        panel.setCanChooseFiles_(True)
        panel.setAllowsMultipleSelection_(False)

        if panel.runModal() == NSOKButton:
                    filename=panel.filename()
        try:
            if os.path.isdir(filename):
                #have to identify which file
                #or figure out how to open .app files using nsopen
                filename=glob.glob(filename+'/Contents/MacOS/*')[0]

                m = MachO(filename)
                for header in m.headers:
                    if header.MH_MAGIC == MH_MAGIC_64:
                        arch = 'systemArch64'
                    else:
                        arch = 'systemArch32'

                if platform.architecture()[0]=='64bit':
                    platArch = 'systemArch64'
                else:
                    platArch = 'systemArch32'
                target=debugger.CreateTarget(str(filename),arch,None,True,error)    #
                self.lldbout.setString_("[+]\tTarget set as: "+filename+"\n")
                # symtab=run_commands(command_interpreter,[str("image dump symtab "+filename.split('/')[-1])]).split('\n')
                # symtab=symtab[7:]

                allFuncs = returnFuntions(target,filename)    
                for i in allFuncs:
                    allFuncsNames.append(i.name)
                
                self.ds.addObjectsFromArray_(allFuncsNames)
                self.tv.setDataSource_(self)
                self.tv.setDelegate_(self)
                self.lldbout.setString_(str(self.lldbout.string())+"\n[+]\tCollecting functions\n")
                self.lldbout.setString_(str(self.lldbout.string())+"[+]\tAnalysis Done\n")
                
        except:
            alert('There was an error while setting target. Please try again!')

    def numberOfRowsInTableView_(self,tv):
            return self.ds.count()

    def tableView_objectValueForTableColumn_row_(self,tv,c,r):
            return str(self.ds.objectAtIndex_(r))

    def tableViewSelectionDidChange_(self,notification):

        funcName = self.ds.objectAtIndex_(self.tv.selectedRow())
        func= allFuncsNames.index(funcName)
        
        op=run_commands(command_interpreter, ['disassemble -n "'+funcName+'"'])
        self.disas.setString_(op)

    def controlTextDidEndEditing_(self,notification):
        cmd=str(self.lldbin.stringValue())
        op=self.runcmd()
        return

if __name__ == "__main__":

    debugger = lldb.SBDebugger.Create()
    debugger.SetAsync (True)
    command_interpreter = debugger.GetCommandInterpreter()
    error = lldb.SBError()
    
    app = NSApplication.sharedApplication()
    viewController = Controller.alloc().initWithWindowNibName_("lldbgui")
    viewController.showWindow_(viewController)
    
    # NSApp.activateIgnoringOtherApps_(True)
    
    from PyObjCTools import AppHelper
    AppHelper.runEventLoop()
