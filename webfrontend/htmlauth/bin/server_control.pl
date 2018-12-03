#!/usr/bin/perl
# 
# Version 2018.12.02
# LoxBerry DNSmasq Plugin Control Server
# 02.12.2018 12:16:22
#

use warnings;
use strict;
use Cwd 'abs_path';
use Config::Simple;
use Data::Dumper;
use LoxBerry::System;
use LoxBerry::Log;

our $pluginconfigfile;
our $plugin_cfg;
our %Config;
our $control_port;
our $dnsmasq_used="off";
our $data;

my %L = LoxBerry::System::readlanguage("language.ini");
my $log = LoxBerry::Log->new ( name => 'DNSmasq' );

LOGSTART	$L{'SERVER_CONTROL.START_CONTROL'};
LOGINF 		$L{'SERVER_CONTROL.SET_DIR_READ_CONF'};

$pluginconfigfile 	= "$lbpconfigdir/DNSmasq.cfg";
$plugin_cfg     	= new Config::Simple("$pluginconfigfile");
if ( !$plugin_cfg )
{
	LOGERR $L{'SERVER_CONTROL.ERR_EMPTY_CONF'}." ".$pluginconfigfile;
	LOGEND $L{'SERVER_CONTROL.ERR_EXIT'};
	exit 1;
}	
else
{
	LOGDEB "Assign config values to variables";

	$control_port = $plugin_cfg->param("default.CONTROL_PORT");
	LOGDEB "CONTROL_PORT = $control_port";

	$dnsmasq_used = $plugin_cfg->param("default.DNSMASQ_USE");
	LOGDEB "DNSMASQ_USE = $dnsmasq_used";

	if ( !$control_port )
	{
		LOGERR $L{'SERVER_CONTROL.ERR_CONF_PARAM_MISSING'}." ".$pluginconfigfile;
		LOGEND $L{'SERVER_CONTROL.ERR_EXIT'};
    	exit 1;
	}	
}

LOGINF $L{'SERVER_CONTROL.INIT_BACKEND_SOCKET'}." ".$control_port;
use IO::Socket::INET;
$| = 1; # auto-flush on socket
 
# creating a listening socket
my $socket = new IO::Socket::INET (
    LocalHost => '0.0.0.0',
    LocalPort => "$control_port",
    Proto => 'tcp',
    Listen => 5,
    Reuse => 1
);

LOGERR $L{'SERVER_CONTROL.ERR_CREATE_SOCKET'}." ".$! unless $socket;
LOGEND $L{'SERVER_CONTROL.ERR_EXIT'} unless $socket;
exit 1 unless $socket;

my $logfile = $log->filename();
LOGOK $L{'SERVER_CONTROL.WAIT_CONNECT'}." ".$control_port;
while(1)
{
    LOGDEB "Waiting for a new client connection";
    my $client_socket = $socket->accept();
 
    LOGDEB "Get information about a newly connected client";

    my $client_address = $client_socket->peerhost();
    LOGDEB "client_address = $client_address";

    my $client_port = $client_socket->peerport();
    LOGDEB "client_port = $client_port";
 
    LOGDEB "Read up to 1024 characters from the connected client";
    $data = "";
    $client_socket->recv($data, 1024);
    LOGDEB "received data: $data";

    if ( "$data" eq "StOp_DNSmasq" )
    {
    	LOGWARN $L{'SERVER_CONTROL.STOP_REQUEST'};
	    system("service dnsmasq stop >>$logfile 2>&1");
		$data = "TXT_CONTROL_DAEMON_OK";
    }
    elsif ( "$data" eq "ReStArT_DNSmasq" )
    {
    	LOGWARN $L{'SERVER_CONTROL.RESTART_REQUEST'};
		system("$lbhomedir/system/daemons/plugins/DNSmasq >>$logfile 2>&1");
		if ($? ne 0) 
		{
			$data = "TXT_CONTROL_DAEMON_FAILED";
		} 
		else 
		{
			$data = "TXT_CONTROL_DAEMON_OK";
		}
    }
    elsif ( "$data" eq "StAtUs_DNSMASQ" )
    {
		LOGINF $L{'SERVER_CONTROL.STATUS_REQUEST'};
	    $data = "DNSMASQ_STATUS_OFF";
		LOGDEB "Checking dnsmasq status";
    	system("service dnsmasq status >>$logfile 2>&1");
	    $data = "DNSMASQ_STATUS_".$?;
    }
    elsif ( "$data" eq "PoRt_cHaNgEd" )
    {
		LOGWARN $L{'SERVER_CONTROL.PORT_CHANGE_REQUEST'};
		LOGDEB "Call $0 and kill me to use new socket.\n";
		$socket->close();
     	system("$0 >>$logfile 2>&1 &");
		LOGEND $L{'SERVER_CONTROL.OK_EXIT'};
		exit 0;
    }
    else
    {
		LOGWARN $L{'SERVER_CONTROL.UNKNOWN_COMMAND'}." => ".$data;
   	    $data = "TXT_CONTROL_UNKNOWN_COMMAND";
    }
   	LOGDEB "Send following data back to client: ".$data;
    $client_socket->send($data);
   	LOGDEB "Closing client socket";
    shutdown($client_socket, 1);
    LOGINF $L{'SERVER_CONTROL.CLIENT_CONN_CLOSED'};
}
$socket->close();
LOGEND $L{'SERVER_CONTROL.OK_EXIT'};
