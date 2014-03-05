#!/usr/bin/python
# -*- coding:utf-8 -*- 
'''
module for common interface
'''
import logging, time, os, threading, sys, shutil, stat, zipfile, StringIO, subprocess
import logging.handlers
from commands import getoutput as call
from PIL import Image

__all__ = ['logger', 'logdeco', 'currenttime', 'mkdir', 'thumbnail', 'Adb', 'Sdb']
'''public API'''

FILE_LOG_LEVEL="DEBUG"
'''File Level'''

CONSOLE_LOG_LEVEL="INFO"
'''Console Level'''

LOCAL_TIME_STAMP_FORMAT = '%Y-%m-%d_%H:%M:%S'
'''local time format'''

REPORT_TIME_STAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
'''report time format'''

LEVELS={"CRITICAL" :50,
        "ERROR" : 40,
        "WARNING" : 30,
        "INFO" : 20,
        "DEBUG" : 10,
        "NOTSET" :0,
       }
'''logger levels'''

def localtime():
    '''
    return time stamp format with LOCAL_TIME_STAMP_FORMAT
    '''
    return time.strftime(LOCAL_TIME_STAMP_FORMAT, time.localtime(time.time()))

def reporttime():
    '''
    return time stamp format with REPORT_TIME_STAMP_FORMAT
    '''
    return time.strftime(REPORT_TIME_STAMP_FORMAT, time.localtime(time.time()))

def forcerm(fn, path, excinfo):
    '''
    force delete a folder
    @type path: string
    @param path: the path of folder
    @type excinfo: string
    @param excinfo: the output info when exception
    '''
    if fn is os.rmdir:
        os.chmod(path, stat.S_IWRITE)
        os.rmdir(path)
    elif fn is os.remove:
        os.chmod(path, stat.S_IWRITE)
        os.remove(path)

def mkdir(path):
    '''
    create a folder
    @type path: string
    @param path: the path of folder
    @rtype: string
    @return: the path of the folder, return None if fail to create folder
    '''
    if os.path.exists(path):
        shutil.rmtree(path, onerror=forcerm)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def thumbnail(img, size=(200,400)):
    '''
    thumbnail a image
    @type img: string
    @param img: the path of image
    @type size: tuple
    @param size: the value of width and height. default is 200,400
    @rtype: a file-like object
    @return: the file-like of the thumbnailed image
    '''
    image = Image.open(img)
    image.thumbnail(size, Image.ANTIALIAS)
    thumb_io = StringIO.StringIO()
    image.save(thumb_io, format='png')
    thumb_io.seek(0)
    return thumb_io

class Sdb(object):
    '''
    class used to call Tizen debug bridge(sdb)
    '''
    def __init__(self):
        '''
        constructor of Sdb
        '''
        self.__sdb_cmd = None

    def sdb(self):
        '''
        get the executable path of sdb
        '''
        if self.__sdb_cmd is None:
            filename = "sdb.exe" if os.name == 'nt' else "sdb"
            sdb_cmd = call('which %s' % filename)
            if not os.path.exists(sdb_cmd):
                raise EnvironmentError('sdb not found from $PATH')
            self.__sdb_cmd = sdb_cmd
        return self.__sdb_cmd

    def cmd(self, *args):
        '''sdb command, add -s serial by default. return the subprocess.Popen object.'''
        cmd_line = ["-s", self.device_serial()] + list(args)
        return self.raw_cmd(*cmd_line)

    def raw_cmd(self, *args):
        '''sdb command. return the subprocess.Popen object.'''
        cmd_line = [self.sdb()] + list(args)
        if os.name != "nt":
            cmd_line = [" ".join(cmd_line)]
        return subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def device_serial(self):
        '''get serial number of device'''
        devices = self.devices()
        if not devices:
            raise EnvironmentError('Device not attached.')
        if 'TIZEN_SERIAL' in os.environ:
            if os.environ["TIZEN_SERIAL"] not in devices:
                raise EnvironmentError("Device %s not connected!" % os.environ["TIZEN_SERIAL"])
        elif len(devices) > 1:
            raise EnvironmentError("Multiple devices attaches but $TIZEN_SERIAL environment incorrect.")
        else:
            os.environ["TIZEN_SERIAL"] = list(devices.keys())[0]
        return os.environ["TIZEN_SERIAL"]

    def devices(self):
        '''get a dict of attached devices. key is the device serial, value is device name.'''
        out = self.raw_cmd("devices").communicate()[0].decode("utf-8")
        match = "List of devices attached"
        index = out.find(match)
        if index < 0:
            raise EnvironmentError("sdb is not working.")
        #sdb ['serial','device','device-1']
        return dict([s.split()[:-1] for s in out[index + len(match):].strip().splitlines() if s.strip()])

    def forward(self, local_port, device_port):
        '''sdb port forward. return 0 if success, else non-zero.'''
        return self.cmd("forward", "tcp:%d" % local_port, "tcp:%d" % device_port).wait()

class Adb(object):
    '''
    class used to call Android debug bridge(adb)
    '''
    def __init__(self, **kwargs):
        '''
        constructor of Adb
        '''
        self.__adb_cmd = None

    def adb(self):
        '''
        get the executable path of adb
        '''
        if self.__adb_cmd is None:
            filename = "adb.exe" if os.name == 'nt' else "adb"
            adb_cmd = call('which %s' % filename)
            if not os.path.exists(adb_cmd):
                raise EnvironmentError('adb not found from $PATH')
            self.__adb_cmd = adb_cmd
        return self.__adb_cmd

    def cmd(self, *args):
        '''adb command, add -s serial by default. return the subprocess.Popen object.'''
        cmd_line = ["-s", self.device_serial()] + list(args)
        return self.raw_cmd(*cmd_line)

    def raw_cmd(self, *args):
        '''adb command. return the subprocess.Popen object.'''
        cmd_line = [self.adb()] + list(args)
        if os.name != "nt":
            cmd_line = [" ".join(cmd_line)]
        return subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def device_serial(self):
        '''get serial number of device'''
        devices = self.devices()
        if not devices:
            raise EnvironmentError('Device not attached.')
        if 'ANDROID_SERIAL' in os.environ:
            if os.environ["ANDROID_SERIAL"] not in devices:
                raise EnvironmentError("Device %s not connected!" % os.environ["ANDROID_SERIAL"])
        elif len(devices) > 1:
            raise EnvironmentError("Multiple devices attaches but $ANDROID_SERIAL environment incorrect.")
        else:
            os.environ["ANDROID_SERIAL"] = list(devices.keys())[0]
        return os.environ["ANDROID_SERIAL"]

    def devices(self):
        '''get a dict of attached devices. key is the device serial, value is device name.'''
        out = self.raw_cmd("devices").communicate()[0].decode("utf-8")
        match = "List of devices attached"
        index = out.find(match)
        if index < 0:
            raise EnvironmentError("adb is not working.")
        #sdb ['serial','device','device-1']
        return dict([s.split()[:] for s in out[index + len(match):].strip().splitlines() if s.strip()])

    def forward(self, local_port, device_port):
        '''adb port forward. return 0 if success, else non-zero.'''
        return self.cmd("forward", "tcp:%d" % local_port, "tcp:%d" % device_port).wait()

class Logger:
    '''
    class used to print log
    '''
    _instance=None
    _mutex=threading.Lock()

    def __init__(self, level="DEBUG"):
        '''
        constructor of Logger
        '''
        self._logger = logging.getLogger("SmartRunner")
        self._logger.setLevel(LEVELS[level])
        self._formatter = logging.Formatter("[%(asctime)s] - %(levelname)s : %(message)s",'%Y-%m-%d %H:%M:%S')
        self._formatterc = logging.Formatter("%(message)s")
        self.add_file_logger()
        self.add_console_logger()

    def add_file_logger(self, log_file="./log/test.log", file_level="DEBUG"):
        '''
        generate file writer
        @type log_file: string
        @param log_file: the path of log file
        @type file_level: string
        @param file_level: the log output level.Defined in global LEVELS
        '''
        logFolder = 'log'
        mkdir(logFolder)
        if not os.path.exists(log_file):
            open(log_file,'w')
            
        fh = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=1024*1024*1,
                                                   backupCount=100,encoding="utf-8")
        fh.setLevel(LEVELS[file_level])
        fh.setFormatter(self._formatter)
        self._logger.addHandler(fh)

    def add_console_logger(self, console_level="INFO"):
        '''
        generate console writer
        @type console_level: string
        @param console_level: the level of console
        '''
        ch = logging.StreamHandler()
        ch.setLevel(LEVELS[console_level])
        ch.setFormatter(self._formatterc)
        self._logger.addHandler(ch)

    @staticmethod
    def getLogger(level="DEBUG"):
        '''
        return the logger instance
        @type level: string
        @param level: the level of logger
        @rtype: Logger
        @return: the instance of Logger      
        '''
        if(Logger._instance==None):
            Logger._mutex.acquire()
            if(Logger._instance==None):
                Logger._instance=Logger(level)
            else:
                pass
            Logger._mutex.release()
        else:
            pass
        return Logger._instance

    def debug(self, msg):
        '''
        print message for debug level
        @type msg: string
        @param msg: the content of msg      
        '''
        if msg is not None:
            self._logger.debug(msg)

    def info(self, msg):
        '''
        print message for info level
        @type msg: string
        @param msg: the content of msg      
        '''
        if msg is not None:
            self._logger.info(msg)

    def warning(self, msg):
        '''
        print message for warning level
        @type msg: string
        @param msg: the content of msg      
        '''
        if msg is not None:
            self._logger.warning(msg)

    def error(self, msg):
        '''
        print message for error level
        @type msg: string
        @param msg: the content of msg      
        '''
        if msg is not None:
            self._logger.error(msg)

    def critical(self, msg):
        '''
        print message for critical level
        @type msg: string
        @param msg: the content of msg      
        '''
        if msg is not None:
            self._logger.critical(msg)

def logdeco(log=None, display_name=None):
    '''
    a wrapper that record the log of function or method and execution time silently and appends to a text file.
    @type log: Logger
    @param log: the instance of Logger
    @type display_name: string
    @param display_name: the display tag 
    '''
    if not log: log = logger
    #if not display_name: display_name = func.__name__
    def wrapper(func):
        def func_wrapper(*args, **kwargs):
            log.debug("enter func: %s" % func.__name__)
            for i, arg in enumerate(args):
                log.debug("\t arguments-%d: %s" % (i + 1, arg))
            for k, v in enumerate(kwargs):
                log.debug("\t dict arguments: %s: %s" % (k, v))
            ts = time.time()
            ret = func(*args, **kwargs)
            te = time.time()
            log.debug('%r (%r, %r) took %.3f seconds' % (func.__name__, args, kwargs, te-ts))
            log.debug("leave func: %s" % func.__name__)
            return ret
        return func_wrapper
    return wrapper

logger = Logger.getLogger()
'''single instance of logger'''
