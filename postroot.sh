
echo `date +"%b  %e %H:%M:%S "`"Check, if DNSmasq Control Daemon is running"                                                                                          
CS_PID=`ps -ef|grep "dnsmasq/bin/server_control.pl"|grep -v grep |awk -F" " '{ print $2 }'`                                                                           
if [ -z "$CS_PID" ]
then
	echo "Not running => ok"
else
	echo "Process ID $CS_PID found, killing it"
	kill -9 $CS_PID;
fi
	echo "Restarting dnsmasq and control daemon in 5 seconds"
	echo `sleep 5;systemctl restart dnsmasq >/dev/null 2>&1; sleep 1; REPLACELBHOMEDIR/system/daemons/plugins/DNSmasq >/dev/null 2>&1`&
exit 0
