#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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
module for stability test runner
'''

from subprocess import Popen as call
from commands import getoutput
from os.path import dirname, abspath, join, exists, splitext, split, basename
import copy, sys, os, datetime, string, argparse, collections
try:
    import xml.etree.ElementTree as ET
except ImportError, e:
    print '[Error: loading module failed, error: %s ]' % e
    sys.exit(1)
try:
    from jinja2 import Environment, FileSystemLoader
except ImportError, e:
    print '[Error: loading module failed, error: %s ]' % e
    print 'You can install jinja2 by typing: '
    print 'easy_install Jinja2 or pip install Jinja2'
    sys.exit(1)
from utils import logdeco, mkdir, Adb, Sdb
from upload import uploader


WORKSPACE = dirname(abspath(__file__))
'''default path of stability runner working directory'''
SCRIPT_WORKSPACE = join(dirname(WORKSPACE), 'scripts')
'''default serach path of test scripts'''
RESULT_OUTPUT_WORKSPACE = join(join(os.getcwd(), 'report'),'scripts')
'''default output path of test result'''
PLAN_OUTPUT_WORKSPACE = join(join(os.getcwd(), 'plan'),'scripts')
'''default output path of test plan'''
PLATFORMS = ('tizen', 'android')
'''default platform list supported by stability runner'''
TIZEN_CONFIG = {'product':'/etc/info.ini:Model=', 'revision':'/etc/info.ini:Build='}
'''default key/values used by SDB to get device configuration from Tizen device'''
ANDROID_CONFIG = {'product':'ro.build.product', 'revision':'ro.build.revision'}
'''default key/values used by adb to get device configuration from Android device'''

def environment(*dpendcy):
    '''
    function used to force checking test environment.
    @type dpendcy: list
    @param dpendcy: the string list of envionment need to be checked. 
    @rtype: None 
    @return: None or raise exception
    '''
    def check_environment(func):
        '''
        a function to check environment dependcy
        '''
        for d in dpendcy: assert getoutput('%s %s' % ('which', d)), '%s not found!' % str(d)
        def wrapper(*argv, **argvs):
            func(*argv, **argvs)
        return wrapper
    return check_environment

def get_device_info(**kwargs):
    '''
    function used to get test session information from DUT
    @type kwargs: dict
    @param kwargs: the key, value of 'platform' and 'device' property
    @rtype: string
    @return: the value of property or None
    '''
    if kwargs['platform'] == 'tizen':
        search = lambda x, tag: [ i.split('=')[-1] for i in x.split() if i.find(tag) != -1][-1]
        sdb = Sdb()
        try:
            deviceid = sdb.device_serial()
            if kwargs['key'] == 'deviceid':
                return deviceid
        except:
            return None
        try:
            ret = str(sdb.raw_cmd('-s', deviceid, 'shell', 'cat', TIZEN_CONFIG[kwargs['key']].split(':')[0]).communicate()[0].decode("utf-8")).replace(';','')
            values = search(ret, TIZEN_CONFIG[kwargs['key']].split(':')[-1])
        except:
            return None
        return values

    if kwargs['platform'] == 'android':
        adb = Adb()
        try:
            deviceid = adb.device_serial()
            if kwargs['key'] == 'deviceid':
                return  deviceid
        except:
            return None
        try:
            ret = adb.raw_cmd('-s', deviceid, 'shell', 'getprop', ANDROID_CONFIG[kwargs['key']]).communicate()[0].decode("utf-8").replace('\r\n', '')
        except:
            return None
        return ret

class Options(object):
    '''
    class used to accept/parse user-input from command-line.
    '''
    def __init__(self, argv):
        '''
        constructor of Options
        '''
        self._opt = self._parse_options().parse_args(argv[1:])
        if self._opt.__dict__['upload']:
            assert self._opt.__dict__['username'], 'no username supplied!'
            assert self._opt.__dict__['password'], 'no password supplied!'
            assert self._opt.__dict__['platform'], 'no platform supplied!'
            
            if self._opt.__dict__['upload']:
                if not self._opt.__dict__['deviceid']:
                    self._opt.__dict__['deviceid'] = get_device_info(platform=self._opt.__dict__['platform'], key='deviceid')
                    if not self._opt.__dict__['deviceid']:
                        while 1:
                            self._opt.__dict__['deviceid'] = raw_input("input device serial number:\n")
                            if not len(self._opt.__dict__['deviceid'].strip()) > 0:
                                print 'device serial number error!\n'
                            else:
                                break

                if not self._opt.__dict__['product']:
                    self._opt.__dict__['product'] = get_device_info(platform=self._opt.__dict__['platform'], key='product')
                    if not self._opt.__dict__['product']:
                        while 1:
                            self._opt.__dict__['product'] = raw_input("input product name:\n")
                            if not len(self._opt.__dict__['product'].strip()) > 0:
                                print 'input product error!\n'
                            else:
                                break

                if not self._opt.__dict__['revision']:
                    self._opt.__dict__['revision'] = get_device_info(platform=self._opt.__dict__['platform'], key='revision')
                    if not self._opt.__dict__['revision']:
                        while 1:
                            self._opt.__dict__['revision'] = raw_input("input revision:\n")
                            if not len(self._opt.__dict__['revision'].strip()) > 0:
                                print 'revision input error!\n'
                            else:
                                break

    def __getitem__(self, name):
        '''
        override to make the call object.attribute available.
        '''
        if not hasattr(self._opt, name):
            raise KeyError('Non-existing argument \'%s\'' % name)
        return getattr(self._opt, name)
    
    def _parse_options(self):
        '''
        init and parse user-input option
        @rtype: argparse.ArgumentParser
        @return: the instance of argparse.ArgumentParser
        '''
        parser = argparse.ArgumentParser(description='Process the paramters of stability test',
                prog='strunner')
        parser.add_argument('-p', '--plan', dest='plan', required=True, action=self._validate_plan(parser),
                            help='Sepcify the test cases plan file (xml)')

        parser.add_argument('--scripts', dest='scripts', default=SCRIPT_WORKSPACE , action=self._validate_scripts(parser),
                            help='Specify the serach directory path of test scripts')

        parser.add_argument('--upload', dest='upload', action='store_true', default=False,
                            help='Upload stability test result to report server. Default is disable')

        parser.add_argument('--username', dest='username',
                            help='Set the account name of account')

        parser.add_argument('--password', '-pwd', dest='password',
                            help='Set the password of account')

        parser.add_argument('--platform', dest='platform', action=self._validate_platform(parser),
                            help='Set the platform type of device')

        parser.add_argument('--product', dest='product',
                            help='Set the product name of device')

        parser.add_argument('--revision', dest='revision',
                            help='Set the revision of device')

        parser.add_argument('--serial', dest='deviceid',
                            help='Set the serial number of device')

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--nonstop', dest='nonstop', action='store_true', 
                            help='Execute test with infinite loop. Default is disable')
        group.add_argument('-c', '--cycle', dest='cycle', type=int, 
                            help='Set the number(int) of loop. execute test with a specified number of loops')
        group.add_argument('-d', '--duration', dest='duration', nargs='+', action=self._validate_duration(parser),
                            help='The minumum test duration before ending the test.\
                                  Here format must follow next format: xxDxxHxxMxxS.\
                                  e.g. --duration=2D09H30M12S, which means 2 days, 09 hours, 30 minutes and 12 seconds')
        return parser

    def _validate_platform(self, parser):
        '''
        validate the name of platform.
        @type parser: argparse.ArgumentParser
        @param parser: the instance of argparse.ArgumentParser
        @rtype: None
        @return: if the platform not support raise exception, else return None
        '''
        class Validation(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if not values in PLATFORMS:
                    parser.error('unknown platform name %s !' % values)
                setattr(namespace, self.dest, values)
        return Validation

    def _validate_plan(self, parser):
        '''
        validate the plan file.
        @type parser: argparse.ArgumentParser
        @param parser: the instance of argparse.ArgumentParser
        @rtype: None
        @return: if the plan file exists return None, else raise exception
        '''
        class Validation(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if not exists(values):
                    parser.error('%s file not found!' % values)
                if not os.path.isfile(values):
                    parser.error('%s is not a file!' % values)
                setattr(namespace, self.dest, values)
        return Validation

    def _validate_scripts(self, parser):
        '''
        validate directory of test scripts.
        @type parser: argparse.ArgumentParser
        @param parser: the instance of argparse.ArgumentParser
        @rtype: None
        @return: if the scripts's directory exists return None, else raise exception
        '''
        class Validation(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if not exists(values):
                    parser.error('%s directory not found!' % values)
                if not os.path.isdir(values):
                    parser.error('%s is not a directory!' % values)
                global SCRIPT_WORKSPACE
                global RESULT_OUTPUT_WORKSPACE
                global PLAN_OUTPUT_WORKSPACE
                SCRIPT_WORKSPACE = os.path.abspath(values)
                PLAN_OUTPUT_WORKSPACE = join(dirname(PLAN_OUTPUT_WORKSPACE), basename(values))
                RESULT_OUTPUT_WORKSPACE = join(dirname(RESULT_OUTPUT_WORKSPACE), basename(values))
                setattr(namespace, self.dest, values)
        return Validation

    def _validate_duration(self, parser):
        '''
        validate the fromat of time stamp.
        @type parser: argparse.ArgumentParser
        @param parser: the instance of argparse.ArgumentParser
        @rtype: None
        @return: if the time format is available return None, else raise exception
        '''
        class Validation(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                value = string.lower(values[-1])
                begin = 0
                days = hours = minutes = seconds = 0
                for i, v in enumerate(value):
                    if v == 'd':
                        days = int(value[begin:i])
                        begin = i + 1
                    elif v == 'h':
                        hours = int(value[begin:i])
                        begin = i + 1
                    elif v == 'm':
                        minutes = int(value[begin:i])
                        begin = i + 1
                    elif v == 's':
                        seconds = int(value[begin:i])
                        begin = i + 1
                if begin == 0:
                    parser.error('%s: duration format error' % values)             
                setattr(namespace, self.dest, datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds))
        return Validation

class StabilityTestRunner(object):
    '''
    class used to drive testkit-lite to execute test.
    '''
    def __init__(self, option, engine='testkit-lite'):
        '''
        Constructor of StabilityTestRunner
        @type option: list 
        @param option: the string list of user-input from command-line
        @type engine: string
        @param engine: the string representation of  the executable application. The default value should be testkit-lite
        @rtype: None
        @return: None
        '''
        self._option = option
        self._engine = engine
        self._converter = None

    @environment('testkit-lite',)
    def run(self):
        '''
        generate the target plan.xml which contains all test cases of one iteration.
        execute the plan.xml with specified mode by test engine. default enginee is testkit-lite. 
        '''
        if self._option['upload']:
            uploader.active(username=self._option['username'], \
                            password=self._option['password'], \
                            platform=self._option['platform'], \
                            product=self._option['product'], \
                            revision=self._option['revision'], \
                            deviceid=self._option['deviceid'])

        if self._option['duration']:
            duration = self._option['duration']
            starttime = datetime.datetime.now()
            cycle_id = 1
            while (datetime.datetime.now() < starttime + duration):
                print 'Testing duration: %s, %s left. \n' % (str(duration), str(duration-(datetime.datetime.now()-starttime)))
                self._execute(cycle_id)
                cycle_id += 1

        elif self._option['cycle']:
            for cycle_id in range(1, self._option['cycle'] + 1):
                print 'Testing cycle %d/%d \n' % (cycle_id, self._option['cycle'])
                self._execute(cycle_id)

        elif self._option['nonstop']:
            cycle_id = 1
            while True:
                self._execute(cycle_id)
                cycle_id += 1

    def _execute(self, cycle_id):
        '''
        drive testkit-lite to execute current test sequences defined by cycle id.
        @type cycle_id: int 
        @param cycle_id: the id of current cycle
        @rtype: None
        @return: None
        '''
        if not self._converter:
            self._converter = convert()
        plan_name = '%s%s%s' % ('cycle_', str(cycle_id), '.xml')
        plan_folder_path = mkdir(PLAN_OUTPUT_WORKSPACE)
        result_output_path = mkdir('%s%s' % (join(RESULT_OUTPUT_WORKSPACE, 'cycle_'), str(cycle_id)))   
        engine_output_path = mkdir(join(result_output_path,'output'))
        result_output_file_path = join(result_output_path,'result.xml')
        destination_xml = self._converter(self._option['plan'], join(plan_folder_path, plan_name), engine_output_path)
        if not destination_xml: raise Exception('the ori plan file parse error!')
        task = '%s %s %s %s %s %s %s' % (self._engine, '-f', destination_xml, '--comm', 'localhost', '-o', result_output_file_path)
        proc = None
        try:
            proc = call(task, shell=True)
            proc.wait()
        except :
            if proc:
                proc.wait()
                sys.exit(1)
        finally:
            if self._option['upload']:
                uploader.upload(cycle_id, result_output_path)
        return cycle_id, result_output_path


def convert():
    '''
    function used to convert original XML file
    @rtype: function
    @return: the function ued to convert test plan file
    '''
    _tid = [1]
    _last_tid = [1]
    def xml_convert(original, destination, output):
        '''
        used to convert the original xml file to be target file. and save the target file in the path of destination
        @type original: string
        @param original: the string path of original xml file
        @type destination: string
        @param destination: the output path of the target xml file
        @type output: string
        @param output: the output path of the teskit-lite
        @rtype: string
        @return: the string path of target xml file. else None if convet failed.
        '''
        tmp_folder, tmp = join(dirname(WORKSPACE), 'templates'), 'template.xml'
        id_seperator = '_'
        sets = collections.OrderedDict()
        tree = ET.parse(original)
        root = tree.getroot()
        suites = root.getchildren()
        if len(suites) != 1:
            raise Exception, "There should be only one suite in plan xml!"
        suitename = suites[0].attrib['name']
        components = suites[0].getchildren()
        total = 0
        c = {}
        for component in components:
            each = 0
            for t in component:
                total += int(t.attrib['loop'])
                each += int(t.attrib['loop'])
            c[component] = each
        _mtotal = [0]
        for component in components:
            _mid = [_tid[0] + _mtotal[0]]
            tcs = list()
            for t in component:
                loop = int(t.attrib['loop'])
                for _id in range(1, loop + 1):
                    tc = dict()
                    tc['order'] = _mid[0]
                    tc['purpose'] = t.attrib['purpose']
                    tc['component'] = component.attrib['name']
                    tc['id'] = '%s%s%s%s%s' % (t.attrib['test_script_entry'].split('.')[0], id_seperator, splitext(split(destination)[-1])[0].split(id_seperator)[-1], id_seperator, str(_id)) 
                    tc['test_script_entry'] = '%s' % (join(SCRIPT_WORKSPACE, t.attrib['test_script_entry']))
                    tc['test_script_entry'] = '%s %s %s' % (tc['test_script_entry'], '-o', join(output, tc['id']))   
                    tc['execution_type'] = t.attrib['execution_type']
                    tc['timeout'] = t.attrib['timeout']
                    _mid[0] += 1
                    tcs.append(tc)
            _mtotal[0] += c[component]
            sets[component.attrib['name']] = tcs
        _last_tid[0] += total
        inner_vars = copy.copy(sets)
        stability_loader = FileSystemLoader(tmp_folder)
        env = Environment(loader=stability_loader, trim_blocks=False)
        template = env.get_template(tmp)
        content =  template.render(data={'suitename':suitename,'cases':inner_vars}) 
        with open(destination, 'wr') as f:
            f.write(content)
        return exists(destination) and abspath(destination) or None
    return xml_convert
