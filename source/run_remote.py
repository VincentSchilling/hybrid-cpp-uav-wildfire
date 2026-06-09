#!/usr/bin/env python3
"""
run_remote.py
 
Startet run_sim_on_raspi.py per SSH auf dem Raspberry Pi und
gibt die Ausgabe live auf der Konsole aus.
 
Zugangsdaten vor der Nutzung in den Konfigurationsvariablen eintragen.
"""
import paramiko
import sys

# individuell anpassen
#----------------------
HOST = ""
USER = ""
PASSWORD = "" 
#---------------------- 

CMD = r"""bash -lc '
cd ~/sim/Masterarbeit 
python3 -u run_sim_on_raspi.py
'"""

def main():
    """Verbindet per SSH mit dem Raspberry Pi und fuehrt run_sim_on_raspi.py aus."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

        stdin, stdout, stderr = ssh.exec_command(CMD, get_pty=True)

        for line in stdout:
            print(line, end="")
        for line in stderr:
            print(line, end="", file=sys.stderr)

        exit_status = stdout.channel.recv_exit_status()
        print(f"\n[Remote Exit-Code: {exit_status}]")
        sys.exit(exit_status)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()