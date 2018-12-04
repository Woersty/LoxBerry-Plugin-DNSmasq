#!/usr/bin/perl
# 
# Version 2018.12.04
# LoxBerry DNSmasq Plugin Control Server
# 04.12.2018 20:59:11
#

# Includes
use warnings;
use strict;
use Cwd 'abs_path';
use Config::Simple;
use LoxBerry::System;
use LoxBerry::Log;

# Variables
my $pluginconfigfile;
my $plugin_cfg;
my %Config;
my $control_port="50003";
my $dnsmasq_used="off";
my $data;
my $logfile = "DNSmasq.log";
my $loglevel = LoxBerry::System::pluginloglevel();
my $loglevel_at_start = $loglevel;

# Read strings
my %L   = LoxBerry::System::readlanguage("language.ini");

# Start Logging
my $log = LoxBerry::Log->new ( name => 'DNSmasq', filename => $lbplogdir ."/". $logfile, append => 1 );
LOGSTART    $L{'SERVER_CONTROL.START_CONTROL'};

# Read config
LOGINF      $L{'SERVER_CONTROL.SET_DIR_READ_CONF'};
$pluginconfigfile   = "$lbpconfigdir/DNSmasq.cfg";
$plugin_cfg         = new Config::Simple("$pluginconfigfile");
if ( !$plugin_cfg )
{
	LOGERR $L{'SERVER_CONTROL.ERR_EMPTY_CONF'}." ".$pluginconfigfile." @".__LINE__;
	LOGINF $L{'SERVER_CONTROL.ERR_EXIT'};
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
		LOGERR $L{'SERVER_CONTROL.ERR_CONF_PARAM_MISSING'}." ".$pluginconfigfile." @".__LINE__;
		LOGWARN $L{'SERVER_CONTROL.ERR_EXIT'};
		exit 1;
	}   
}

# Server Control Program
LOGINF $L{'SERVER_CONTROL.INIT_BACKEND_SOCKET'}." ".$control_port;
use IO::Socket::INET;
$| = 1; # auto-flush on socket
 
# Creating a listening socket
my $socket = new IO::Socket::INET ( LocalHost => '0.0.0.0', LocalPort => "$control_port", Proto => 'tcp',	Listen => 5, Reuse => 1);
LOGERR $L{'SERVER_CONTROL.ERR_CREATE_SOCKET'}." ".$!." @".__LINE__ unless $socket;
LOGWARN $L{'SERVER_CONTROL.ERR_EXIT'} unless $socket;
exit 1 unless $socket;

# Get logfile name
my $logfilename = $log->filename();

# Start endless loop
LOGOK $L{'SERVER_CONTROL.WAIT_CONNECT'}." ".$control_port." (TCP)";
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
	LOGDEB "Select action";
	if ( "$data" eq "StOp_DNSmasq" )
	{
		LOGWARN $L{'SERVER_CONTROL.STOP_REQUEST'};
		system("cd; service dnsmasq stop >>$logfilename 2>&1") if ( $loglevel eq 7 );
		system("cd; service dnsmasq stop >/dev/null 2>&1")     if ( $loglevel ne 7 );
		sleep 1;
		$data = "TXT_CONTROL_DAEMON_OK";
	}
	elsif ( "$data" eq "ReStArT_DNSmasq" )
	{
		LOGWARN $L{'SERVER_CONTROL.RESTART_REQUEST'};
		system("cd; $lbhomedir/system/daemons/plugins/DNSmasq >>$logfilename 2>&1") if ( $loglevel eq 7 );
		system("cd; $lbhomedir/system/daemons/plugins/DNSmasq >/dev/null 2>&1")     if ( $loglevel ne 7 );
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
		system("cd; service dnsmasq status >>$logfilename 2>&1") if ( $loglevel eq 7 );
		system("cd; service dnsmasq status >/dev/null 2>&1")     if ( $loglevel ne 7 );
		sleep 1;
		$data = "DNSMASQ_STATUS_".$?;
	}
	elsif ( "$data" eq "PoRt_cHaNgEd" )
	{
		LOGWARN $L{'SERVER_CONTROL.PORT_CHANGE_REQUEST'};
		LOGDEB "Call $0 and kill me to use new socket.";
		$socket->close();
		system("cd; $0 >/dev/null 2>&1 &");     
		LOGINF $L{'SERVER_CONTROL.OK_EXIT'};
		exit;
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

	##### START Workaround for https://github.com/mschlenstedt/Loxberry/issues/835
	my $plugindb_file = "$lbsdatadir/plugindatabase.dat";
	LOGWARN "No plugindb_file at $plugindb_file" if (!-e $plugindb_file);
	my $openerr;
	open(my $fh, "<", $plugindb_file) or ($openerr = 1);
	if ($openerr) 
	{
		LOGWARN "Error opening $plugindb_file" 
	}
	else
	{
		my @data = <$fh>;
		close $fh;
		foreach (@data)
		{
			if ($_ =~ /DNSmasq/)
			{
				my @array=split(/\|/,$_);
				$loglevel=int($array[11]);
				last;
			}
		}
	} ;
	##### END Workaround for https://github.com/mschlenstedt/Loxberry/issues/835
	if ( $loglevel ne $loglevel_at_start )
	{
		LOGWARN $L{'SERVER_CONTROL.LOGLEVEL_CHANGED'}." (".$loglevel_at_start." => ".$loglevel.")"; 
		LOGDEB "Restarting $0 ...";
		$socket->close();
		system("cd; $0 >/dev/null 2>&1 &");     
		LOGINF $L{'SERVER_CONTROL.OK_EXIT'};
		exit;
	}
}
$socket->close();
LOGINF $L{'SERVER_CONTROL.OK_EXIT'};
