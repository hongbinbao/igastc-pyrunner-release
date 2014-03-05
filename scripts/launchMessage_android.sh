#!/bin/bash

/opt/gui-smoke-test/igas-android -t /home/ethan/Desktop/Intel-TestFramework/iGAS/editor/case_editor/launchMessage/launchMessage.xml -e /opt/gui-smoke-test/zeeyabeach.android.execcontext.xml -o $2

RET=$?
if [ $RET -eq 0 ];then
   echo "Launch Message application success"
   RETVALUE=0
else 
   echo "Launch Message application failed"
   RETVALUE=1
fi


exit $RETVALUE
