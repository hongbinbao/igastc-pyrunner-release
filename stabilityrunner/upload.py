#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Intel Corporation
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.
#
# Authors:
#              Bao, Hongbin <bongbinx.bao@intel.com>

'''
module for stability test result upload
'''

import requests
import glob
from uuid import uuid1
from ConfigParser import ConfigParser
import json, hashlib, math, time, threading, sys
from os.path import join, exists
from utils import logger, logdeco, reporttime, thumbnail

__all__ = ['uploader']
'''export API'''

MAXIMUM_RETRY_COUNT = 3
'''the maxuimum retry times when http request failed'''
def get_url_from_file(name):
    '''
    read server API from server.config file
    @type name: string
    @param name: the name section of in server.config file.
    @rtype: dict
    @return: the dictionary contains the server configuration
    '''
    cf = ConfigParser()
    cf.read('server.config')
    return cf.get('url', name)

def retry(tries, delay=1, backoff=2):
    '''
    retries a function or method until it returns True.
    delay sets the initial delay, and backoff sets how much the delay should
    lengthen after each failure. backoff must be greater than 1, or else it
    isn't really a backoff. tries must be at least 0, and delay greater than 0.
    @type tries: int
    @param tries: the retry times
    @type delay: int
    @param delay: the retry duration from last request to next request
    @type backoff: int
    @param backoff: used to make the retry duration wait longer
    @rtype: boolean
    @return: True if the function return True. else return False
    '''

    if backoff <= 1: 
        raise ValueError("backoff must be greater than 1")
    tries = math.floor(tries)
    if tries < 0: 
        raise ValueError("tries must be 0 or greater")
    if delay <= 0: 
        raise ValueError("delay must be greater than 0")
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay # make mutable
            rv = f(*args, **kwargs) # first attempt
            while mtries > 0:
                if rv != None or type(rv) == str or type(rv) == dict: # Done on success ..
                    return rv
                mtries -= 1      # consume an attempt
                time.sleep(mdelay) # wait...
                mdelay *= backoff  # make future wait longer
                rv = f(*args, **kwargs) # Try again
            print 'retry %d times all failed. plese check server status' % tries
            sys.exit(1)
            return False # Ran out of tries
        return f_retry # true decorator -> decorated function
    return deco_retry  # @retry(arg[, ...]) -> true decorator

@logdeco()
@retry(MAXIMUM_RETRY_COUNT)
def request(method, url, data=None, **kwargs):
    '''
    sends a HTTP request.
    @type method: string
    @param method: the request type of http method(get, post, put, delete)
    @type url: string
    @param url: URL for the request
    @type data: dict
    @param data: (optional) Dictionary, bytes, or file-like object to send in the body of http protocol
    @type kwargs: dict
    @param kwargs:  Optional arguments that request takes
    @rtype: boolean
    @return: True if the HTTP request success, else return False
    '''
    ret = None
    m = method.lower()
    if m in ('get', 'post', 'put', 'delete'):
        req = getattr(requests, m, None)
    try:
        #ret = req(url=url, data=data, **kwargs).json()
        r = req(url=url, data=data, **kwargs)
        if r:
            ret = r.json()
    except requests.exceptions.Timeout, e:
        print e
    except requests.exceptions.TooManyRedirects:
        print e
    except requests.exceptions.RequestException as e:
        print e
    except Exception, e:
        print e
    return ret

class Uploader(object):
    '''
    class used to create/update, file upload and get token from report server
    '''
    def __init__(self):
        '''
        constructor of Uploader
        '''
        self._session_id = None
        self._session_info = None
        self._token = None
        self._is_regist = False

    def active(self, **session_properties):
        '''
        used to regist test session on report server
        @type session_properties: dict
        @param session_properties: the dictionary of session properties
        @rtype: boolean
        @return: True if active success, else return False    
        '''
        self._session_id = str(uuid1())
        self._session_info = {'subc':'create', \
                              'data':{'planname':'test.plan', \
                                      'starttime':reporttime(), \
                                      'deviceinfo':{'product':session_properties['product'], \
                                                    'revision':session_properties['revision'], \
                                                    'deviceid':session_properties['deviceid'] \
                                                   }
                                     }
                              }
        print '\r\t'
        print 'test session properties:'
        print self._session_info
        print '\nregisting on stability server...'
        self._token = Authentication.getToken(session_properties['username'] , session_properties['password'])
        self._is_regist = Authentication.regist(self._session_id, self._token, self._session_info)
        print 'success\nsession id: %s \ntoken: %s\n\n' % (self._session_id, self._token)
        return self._is_regist

    def upload(self, cycle_id, result_path):
        '''
        method used to upload result file, log and snapshot
        @type cycle_id: int
        @param cycle_id: the id of current test cycle
        @type result_path: string
        @param result_path: the output path of test result
        @rtype: None
        @return: if session regist not success raise exception, else return None
        '''
        if not self._is_regist:
            raise 'session dosen\'t regist.'
        UploadThread(self._session_id, self._token , cycle_id, result_path).start()

class Authentication(object):

    @staticmethod
    def regist(session_id, token, session_info):
        '''
        regist session on server
        @type session_id: int
        @param session_id: the unique id of current test session
        @type token: string
        @param token: the token got from report server
        @type session_info: dict
        @param session_info: the dictionary of session properties
        @rtype: dict
        @return: a dictionary contains the feedback content from report server. 
        '''
        url = get_url_from_file('session_create') % session_id
        session_info['token'] = token
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        r = request(method='post', url=url, data=json.dumps(session_info), headers=headers, timeout=3)
        return r

    @staticmethod
    def getToken(username, password, appid='01'):
        '''
        get the session token from server.
        @type username: string 
        @param username: the account name
        @type password: string
        @param password: the account password
        @type appid: string
        @param appid: the id of client side, always be '01'
        @rtype: string
        @return: the value of token, else return None if fail to get token from report server
        '''
        ret = None
        m = hashlib.md5()
        m.update(password)
        pwd = m.hexdigest()
        values = {'subc': 'login', 'data':{'appid':'01', 'username':username, 'password':pwd}}
        url = get_url_from_file('auth')
        headers = {'content-type': 'application/json', 'accept': 'application/json'}
        r = request(method='post', url=url, data=json.dumps(values), headers=headers, timeout=3)
        return r and r['data']['token'] or None

class UploadThread(threading.Thread):
    '''
    Thread class used to upload result file/log/snapshot.
    '''
    def __init__(self, session_id, token, cycle_id, path, callback=None):
        '''
        constructor of UploadThread
        @type session_id: string 
        @param session_id: the unique id of current test session
        @type token: string
        @param token: the token got from report server
        @type cycle_id: int
        @param cycle_id: the id of current cycle
        @type path: string
        @param path: the result output path
        @type callback: function
        @param callback: a function to callback before thread finish       
        '''
        super(UploadThread, self).__init__(name='%s%s' % ('upload-', str(cycle_id)))
        #self.daemon = True
        self._is_stop = False
        self._session_id = session_id
        self._token = token
        self._cycle_id = cycle_id
        self._path = path
        self._callback = callback

    def run(self):
        '''
        thread work method.
        '''
        try:
            logger.debug('>>>enter run...')
            logger.debug('uploading thread %s' % threading.current_thread().name)
            assert exists(self._path)
            xmlfile = join(self._path,'result.xml')
            url = get_url_from_file('session_update') % self._session_id
            values = {'token':self._token, 'endtime':reporttime()}
            files = {'file': open(xmlfile, 'rb')}
            logger.debug('begin to upload whole result file')
            ret = request(method='post', url=url, files=files, data=values, timeout=60)
            logger.debug('end to upload whole result file')
            if (not ret) or (not ret['result'] == 'ok') or (not 'failures' in ret['data']):#error
                logger.debug('server no return failures list')
                return
            if not ret['data']['failures']:
                logger.debug('server return failures is none')
                return
            failures = [ {failure['tid']: join(join(self._path, 'output'), failure['caseid'])} for failure in ret['data']['failures']]
            file_upload_url = get_url_from_file('file_upload')
            for f in failures:
                tid, path = f.popitem()
                _file_upload_url = file_upload_url % (self._session_id, str(tid))
                if not exists(path): return
                #mock igas output
                #import shutil
                #os.mkdir(path)
                #shutil.copyfile('/home/test/Desktop/x_failure_a.png', join(path,'x_failure_a.png'))
                #shutil.copyfile('/home/test/Desktop/b_ori_dd.png', join(path,'b_ori_dd.png'))
                #shutil.copyfile('/home/test/Desktop/log.zip', join(path,'log.zip'))
                snapshots_list = [ s for s in glob.glob(join(path,'*.png')) if s.find('fail') != -1 or s.find('ori') != -1 ]
                expect_snapshot = [join(path, e) for e in snapshots_list if e.find('ori') != -1]
                current_snapshot = [join(path, c) for c in snapshots_list if c.find('fail') != -1]
                logger.debug('expect snapshot:')
                logger.debug(str(expect_snapshot))
                logger.debug('current snapshot:')
                logger.debug(str(current_snapshot))               
                for c in current_snapshot:
                    ###img = thumbnail(c)
                    ###files = {'file': img}
                    files = {'file': open(c, 'rb')}
                    #dirs, name =  split(c)
                    headers = {'Content-Type':'image/png', 'Ext-Type':'%s%s%s' % ('current', ':', 'step')}
                    ret = request(method='put', url=_file_upload_url, headers=headers, data=files['file'])
                    logger.debug('uploading expected snapshots done')
                for s in expect_snapshot:
                    ###img = thumbnail(s)
                    ###files = {'file': img}
                    #orig
                    files = {'file': open(s, 'rb')}
                    #dirs, name =  split(s)
                    headers = {'Content-Type':'image/png', 'Ext-Type':'%s%s%s' % ('expect', ':', 'step')}
                    ret = request(method='put', url=_file_upload_url, headers=headers, data=files['file'])
                    logger.debug('uploading current snapshots done')
                log = join(path, 'log.zip')
                if not exists(log): return
                files = {'file': open(log, 'rb')}
                headers = {'Content-Type':'application/zip'}
                ret = request(method='put', url=_file_upload_url, headers=headers, data=files['file'])
                logger.debug('uploading log file done')
        except Exception, e:
            logger.debug(str(e))
            self.stop()
        finally:
            if self._callback: self._callback()

    def stop(self):
        '''
        stop current runnning thread.
        '''
        self._is_stop = True

uploader = Uploader()
'''single instance of Uploader'''
