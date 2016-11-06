#!/usr/bin/perl
# 
# Version 1.0
# LoxBerry DNSmasq Plugin Control Server
# 06.11.2016 12:39:47
#

use warnings;
use strict;
use Cwd 'abs_path';
use Config::Simple;
use Data::Dumper;

our $psubfolder;
our $cfg;
our $home;
our $installfolder;
our $pluginconfigdir;
our $pluginconfigfile;
our $plugin_cfg;
our %Config;
our $control_port;
our $dnsmasq_used="off";
our $data;

# Figure out in which subfolder we are installed
$home       = abs_path($0);
$home       =~ s/(.*)\/(.*)\/(.*)\/(.*)\/(.*)\/(.*)\/(.*)$/$1/g;
$psubfolder = abs_path($0);
$psubfolder =~ s/(.*)\/(.*)\/(.*)\/(.*)$/$2/g;

#Set directories + read LoxBerry config
$cfg              = new Config::Simple("$home/config/system/general.cfg");
$installfolder    = $cfg->param("BASE.INSTALLFOLDER");

#Set directories + read Plugin config
$pluginconfigdir  = "$home/config/plugins/$psubfolder";
$pluginconfigfile = "$pluginconfigdir/DNSmasq.cfg";
$plugin_cfg     = new Config::Simple("$pluginconfigfile");
if ( !$plugin_cfg )
{
	print "Error: Empty config file ($pluginconfigfile)\nKill myself!\n";
	exit 1;
}	
else
{
	$control_port = $plugin_cfg->param("default.CONTROL_PORT");
	$dnsmasq_used = $plugin_cfg->param("default.DNSMASQ_USE");
	if ( !$control_port )
	{
		print "Error: CONTROL_PORT=xxxxx Parameter missing in config file.\nKill myself!\n";
    exit 1;
	}	
}

use IO::Socket::INET;
 
# auto-flush on socket
$| = 1;
 
# creating a listening socket
my $socket = new IO::Socket::INET (
    LocalHost => '0.0.0.0',
    LocalPort => "$control_port",
    Proto => 'tcp',
    Listen => 5,
    Reuse => 1
);
die "cannot create socket $!\n" unless $socket;
print "DNSmasq control server waiting for client connection on port $control_port\n";
 
while(1)
{
    # waiting for a new client connection
    my $client_socket = $socket->accept();
 
    # get information about a newly connected client
    my $client_address = $client_socket->peerhost();
    my $client_port = $client_socket->peerport();
 
    # read up to 1024 characters from the connected client
    $data = "";
    $client_socket->recv($data, 1024);
    #print "received data: $data\n";

    if ( "$data" eq "StOp_DNSmasq" )
    {
	    	system("service dnsmasq stop 2>&1 >/dev/null");
		    $data = "TXT_CONTROL_DAEMON_OK";
    }
    elsif ( "$data" eq "ReStArT_DNSmasq" )
    {
     	  system("$home/system/daemons/plugins/DNSmasq");
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
	    $data = "DNSMASQ_STATUS_OFF";
			$plugin_cfg = new Config::Simple("$pluginconfigfile");
			if ( $plugin_cfg )
			{
				$dnsmasq_used = $plugin_cfg->param("default.DNSMASQ_USE");
				if ( $dnsmasq_used eq "on" )
				{
		    	system("service dnsmasq status 2>&1 >/dev/null");
			    $data = "DNSMASQ_STATUS_".$?;
				}
			}
    }
    elsif ( "$data" eq "PoRt_cHaNgEd" )
    {
				print "Call $0 and kill me to use new socket.\n";
     	  system("$0 &");
				exit 0;
    }
    else
    {
   	    $data = "TXT_CONTROL_UNKNOWN_COMMAND";
    }
    $client_socket->send($data);
    shutdown($client_socket, 1);
}
$socket->close();
