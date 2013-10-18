#!/usr/bin/env python

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.resource import Resource
from random import choice
import string, cgi, time, pyinotify, threading, sys, urllib2, os, argparse

userAgentKeys = ["chrome","safari","firefox","opera","msie"]
extentions = ["css","xml","html","php","js","asp","png","jpeg","jpg","gif"]
options = None

js = """
 Reloader = {
    busy: false,
    interval: null,
    script: null,
    host: null,
    lastRequest: 0,
    init: function(){
        var self = this;
        this.host = 'http://127.0.0.1:8181/check/';
        this.interval = setInterval(function(){
            try{
                if(!self.busy){
                    self.lastRequest = new Date().valueOf();
                    self.busy = true;
                    self.sendRequest();
                }else if(new Date().valueOf() - self.lastRequest > 5){
                    self.busy = false;
                }
            }catch(er){}
        },500);
    },
    sendRequest: function(){
        if(document.body){
            this.script = document.createElement('script');
            this.script.type = 'text/javascript';
            this.script.async = true;
            this.script.src = this.host + '?cacheBuster=' + new Date().valueOf().toString();
            document.body.appendChild(this.script);
        }
    },
    callback: function(data){
        this.busy = false;
        this.reload(data);
        document.body.removeChild(this.script);
    },
    reload: function(type){
        if(type === 'css'){ this.updateCss();}
        else if(type === 'refresh'){ window.location.reload(true); }
    },
    updateCss: function(){
        var a = document.getElementsByTagName('link');
        for(var i=0;i<a.length;i++) {
            var s = a[i];
            if(s.rel.toLowerCase().indexOf('stylesheet')>=0&&s.href) {
                var h = s.href.replace(/(\&|\\?)cacheBuster=\d*/,'');
                s.href= h + (h.indexOf('?')>=0?'&':'?') +'cacheBuster='+ (new Date().valueOf());
            }
        }
    }
}

Reloader.init();
"""


class UpdateManager():
    browsers = {}
    update = "none"
    lock = threading.RLock()
        
    @staticmethod
    def getUpdate(request):
        result = "none"
        UpdateManager.lock.acquire()
        try:
            browserId = request.getCookie("reloader")
            if browserId == None or len(browserId) != 14:
                browserId = ''.join([choice(string.letters + string.digits) for i in range(14)])
                request.addCookie("reloader",browserId)
            if browserId in UpdateManager.browsers.keys():
                if UpdateManager.browsers[browserId] == False:
                    UpdateManager.browsers[browserId] = True
                    result = UpdateManager.update
            else:
                UpdateManager.browsers[browserId] = True
                result = UpdateManager.update           
        finally:
            UpdateManager.lock.release()
        userAgent = request.getHeader("User-Agent").lower()
        if userAgent != None:
            for key in userAgentKeys:
                if key in userAgent:
                    userAgent = key
                    break
        if result != "none": print "==> Update %s sent to %s : %s" % (result,browserId,userAgent)
        return result;
            
    @staticmethod
    def setUpdate(update):
        UpdateManager.lock.acquire()
        try:
            if UpdateManager.update == update: print "==> Resetting Update: %s" % update
            else: print "==> Setting Update: %s" % update
            UpdateManager.update = update
            for key in UpdateManager.browsers.keys(): UpdateManager.browsers[key] = False
        finally:
            UpdateManager.lock.release()
            
class OnWriteHandler(pyinotify.ProcessEvent):
    
    lastFile = { "path":None, "time":0.0 }
    
    def my_init(self, cwd):
        self.cwd = cwd
        
    def process_IN_MODIFY(self, event):
                
                if OnWriteHandler.lastFile["path"] == event.pathname and time.time() - OnWriteHandler.lastFile["time"] < 1: 
                        if options.verbose: print "FILE MODIFIED (IGNORED DUPLICATE EVENT): %s" % event.pathname
                        return
                OnWriteHandler.lastFile["path"] = event.pathname
                OnWriteHandler.lastFile["time"] = time.time()
                name = event.name.lower()
                if name.endswith(".css"): 
                        UpdateManager.setUpdate("css")
                        if options.verbose: print "FILE MODIFIED: %s" % event.pathname
                elif options.strict:
                        dotPos = name.find('.')
                        if dotPos != -1 and name[dotPos+1:] in extentions: 
                                UpdateManager.setUpdate("refresh")
                                if options.verbose: print "FILE MODIFIED: %s" % event.pathname
                        elif options.verbose: print "FILE MODIFIED (IGNORED): %s" % event.pathname
                else:
                        UpdateManager.setUpdate("refresh")
                        if options.verbose: print "FILE MODIFIED: %s" % event.pathname

class MonitorThread(threading.Thread):
    
    def setPath(self,path):
                self.path = path
        
    def run(self):
                wm = pyinotify.WatchManager()
                handler = OnWriteHandler(cwd=self.path)
                self.notifier = pyinotify.ThreadedNotifier(wm, default_proc_fun=OnWriteHandler(cwd=self.path))
                wm.add_watch(self.path, pyinotify.ALL_EVENTS, rec=True, auto_add=True)
                self.notifier.start()
        
    def stopMonitor(self):
                self.notifier.stop()

class JsPage(Resource):
    
    isLeaf = True
    
    def render_GET(self, request):
                request.setHeader("Content-Type","application/javascript")
                print "==> Reloader.js request"
                return js

class CheckPage(Resource):
    
    isLeaf = True
    
    def render_GET(self, request):
                request.setHeader("Content-Type","application/javascript")
                return "Reloader.callback('%s');" % UpdateManager.getUpdate(request)
        
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', dest='path', help='the directory to monitor')
    parser.add_argument('-s','--strict', dest='strict', action='store_true')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
    options = parser.parse_args()
       
    if options.path == None or not os.path.isdir(options.path): 
        print parser.print_help()
        sys.exit(0)   
    
    monitor = MonitorThread()
    monitor.setPath(options.path)
    monitor.start();
    
    print '\nAdd this to your page <head>:\n\n\t<script type="text/javascript" src="http://127.0.0.1:8181/js"></script>\n';
    print 'Monitoring %s' % options.path
    print 'Server Listening on port 8181'    
    print '(Ctrl-C to exit)\n'
    
    root = Resource()
    root.putChild("js",JsPage())
    root.putChild("check",CheckPage())
    reactor.listenTCP(8181, Site(root))
    reactor.run()
    
    print "shutting down..."
    monitor.stopMonitor()
