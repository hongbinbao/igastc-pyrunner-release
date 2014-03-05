
stability runner is a wrapper of testkit-lit to execute test case specified by testkit-lit.
provide the loop and upload feature.

===============================stability runner command line options===================================================
~/stabilityrunner$ strunner -h
usage: strunner [-h] -p PLAN [--scripts SCRIPTS] [--upload]
                [--username USERNAME] [--password PASSWORD]
                [--platform PLATFORM] [--product PRODUCT]
                [--revision REVISION] [--serial DEVICEID]
                (--nonstop | -c CYCLE | -d DURATION [DURATION ...])

Process the paramters of stability test

optional arguments:
  -h, --help            show this help message and exit
  -p PLAN, --plan PLAN  Sepcify the test cases plan file (xml)
  --scripts SCRIPTS     Specify the serach directory path of test scripts
  --upload              Upload stability test result to report server. Default
                        is disable
  --username USERNAME   Set the account name of account
  --password PASSWORD, -pwd PASSWORD
                        Set the password of account
  --platform PLATFORM   Set the platform type of device
  --product PRODUCT     Set the product name of device
  --revision REVISION   Set the revision of device
  --serial DEVICEID     Set the serial number of device
  --nonstop             Execute test with infinite loop. Default is disable
  -c CYCLE, --cycle CYCLE
                        Set the number(int) of loop. execute test with a
                        specified number of loops
  -d DURATION [DURATION ...], --duration DURATION [DURATION ...]
                        The minumum test duration before ending the test. Here
                        format must follow next format: xxDxxHxxMxxS. e.g.
                        --duration=2D09H30M12S, which means 2 days, 09 hours,
                        30 minutes and 12 seconds

example:
  without result upload option:
  strunner -p original_plan.xml --duration 8D 
  strunner -p original_plan.xml --cycle 10
  strunner -p original_plan.xml --nonstop
  strunner -p original_plan.xml --scripts location_of_scripts --nonstop

  with result upload option:
  strunner -p original_plan.xml -c 10 --upload --username x --password x --platform tizen --product m0 --revision x --serial xx

======================stability test scripts deploy====================================
1: copy your scripts to "stabilityrunner/scripts" directory
2: add your test script name into original_plan.xml
3: add your report server configuration into server.config file
4: execute test from command line

=================================the original_plan.xml=================================
how to add your test script into original_plan.xml:
<component name="Email">
        <testcase test_script_entry="ChkEmail_Launch.sh" purpose="Check Email launch" loop="3" timeout="180"/>
        <testcase test_script_entry="ChkPhone_Launch.sh" purpose="Check Phone launch" loop="5" timeout="90"/>
</component>

detail: refer to "stabilityrunner/stability.xsd"
<component>
     name: the component name which the test script belong to
<testcase>
     test_script_entry: the test case name under "stabilityrunner/scripts" directory
     purpose: the test case description
     loop: the test case execute counts in each cycle.
     timeout: the test case timeout value in seconds







=======================device internal/external storage setup command line options=====================
usage: stsetup [-h] [-i INTERNAL] [-e EXTERNAL] [-p PERCENT] [-f] [-c] [--fillup]
            [-s SERIAL]

Process the paramters of setup tool

optional arguments:
  -h, --help            show this help message and exit
  -i INTERNAL, --internal INTERNAL
                        Set the path of device internal storage which need to
                        be filled.
  -e EXTERNAL, --external EXTERNAL
                        Set the path of device external storage which need to
                        be filled.
  -p PERCENT, --percent PERCENT
                        Set the maximum percent value of storage need to be
                        filled to
  -f, --force           Set the type of file need to be filled.
  -c, --cleanup         Set the type of file need to be filled.
  --fillup              Set the type of file need to be filled.
  -s SERIAL             Set the device serial number.

example:
   fill internal and external storage to 95%: stsetup -p 0.95
   delete the filled storage: stsetup --cleanup

=========================package structure=======================================
.
├── LICENSE
├── log
│   └── test.log
├── log.pyc
├── original_plan.xml
├── plan
│   ├── cycle_1.xml
│   └── cycle_2.xml
├── README.md
├── releasenote
├── result
│   ├── cycle_1
│   │   ├── output
│   │   └── result.xml
│   └── cycle_2
│       ├── output
│       └── result.xml
├── scripts
│   ├── addAlarm.xml
│   └── callFromPhoneBook.xml
├── server.config
├── stabilityrunner
│   ├── __init__.py
│   ├── log.py
│   ├── runner.py
│   ├── st.sh
│   ├── upload.py
├── stability.xsd
├── strunner
├── stsetup
├── templates
│   └── template.xml
├── tests
└── TODO.md
